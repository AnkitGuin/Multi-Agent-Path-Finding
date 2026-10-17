"""Zero-dependency HTTP server for the interactive MAPF demo.

Routes
------
``GET  /``              the single-page application
``GET  /api/health``    liveness + planner list
``POST /api/generate``  build a scenario from the requested parameters
``POST /api/solve``     run one or more planners on the given scenario

The algorithmic logic lives in ``planning/``; this module only marshals JSON.
It uses the standard library on purpose (no Flask/FastAPI needed) and binds to
``0.0.0.0`` so it works behind the sandbox preview proxy.

    python -m app.server --port 8000
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any, Dict, List, Tuple
from urllib.parse import urlparse

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from environment.generators import generate_scenario, instance_features  # noqa: E402
from environment.grid import GridMap, Scenario  # noqa: E402
from evaluation.metrics import (  # noqa: E402
    check_planner_result,
    sum_of_individual_costs,
)
from planning import PLANNERS, solve  # noqa: E402
from planning.collisions import detect_conflicts  # noqa: E402

STATIC_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "static")
DEFAULT_TIME_LIMIT = 5.0
MAX_TIME_LIMIT = 60.0


# --------------------------------------------------------------------------- #
#  (de)serialisation helpers -- grids travel as ASCII rows: compact and readable
# --------------------------------------------------------------------------- #
def grid_to_payload(grid: GridMap) -> Dict[str, Any]:
    return {
        "width": grid.width,
        "height": grid.height,
        "rows": ["".join("@" if (x, y) in grid.obstacles else "." for x in range(grid.width))
                 for y in range(grid.height)],
    }


def grid_from_payload(payload: Dict[str, Any]) -> GridMap:
    rows = payload["rows"]
    obstacles = {
        (x, y) for y, row in enumerate(rows) for x, ch in enumerate(row) if ch != "."
    }
    return GridMap(
        width=payload["width"], height=payload["height"], obstacles=obstacles, name="custom"
    )


def scenario_from_payload(payload: Dict[str, Any]) -> Scenario:
    grid = grid_from_payload(payload["grid"])
    return Scenario(
        grid=grid,
        starts=[tuple(c) for c in payload["starts"]],
        goals=[tuple(c) for c in payload["goals"]],
        name=payload.get("name", "demo"),
    )


def planner_payload(scenario: Scenario, result, sic: Any) -> Dict[str, Any]:
    """One planner outcome as JSON, including enough detail to animate it."""
    conflicts = detect_conflicts(result.paths, max_conflicts=400) if result.paths else []
    return {
        "algorithm": result.algorithm,
        "success": bool(result.success),
        "status": result.status,
        "runtime_sec": round(result.runtime_sec, 4),
        "soc": result.soc,
        "makespan": result.makespan,
        "sic": sic,
        "soc_gap": (round(result.soc / sic - 1.0, 4) if (result.soc and sic) else None),
        "paths": [[[int(x), int(y)] for (x, y) in path] for path in result.paths],
        "conflicts_initial": result.conflicts_initial,
        "conflicts_final": len(conflicts),
        "conflict_events": [
            {"t": c.t, "kind": c.kind, "cell": [int(c.cell1[0]), int(c.cell1[1])]}
            for c in conflicts
        ],
        "high_level_expansions": result.high_level_expansions,
        "low_level_calls": result.low_level_calls,
        "low_level_expansions": result.low_level_expansions,
        "priority_order": result.priority_order,
        "details": {k: v for k, v in result.details.items() if isinstance(v, (str, int, float))},
    }


# --------------------------------------------------------------------------- #
#  Request handlers
# --------------------------------------------------------------------------- #
def handle_generate(payload: Dict[str, Any]) -> Dict[str, Any]:
    scenario = generate_scenario(
        width=int(payload.get("width", 32)),
        height=int(payload.get("height", 32)),
        num_agents=int(payload.get("num_agents", 10)),
        obstacle_density=float(payload.get("obstacle_density", 0.2)),
        structure=str(payload.get("structure", "random")),
        distribution=str(payload.get("distribution", "uniform")),
        seed=int(payload.get("seed", 0)),
    )
    return {
        "grid": grid_to_payload(scenario.grid),
        "starts": [list(c) for c in scenario.starts],
        "goals": [list(c) for c in scenario.goals],
        "name": scenario.name,
        "features": instance_features(scenario),
        "obstacle_density_measured": round(scenario.grid.obstacle_density, 4),
    }


def handle_solve(payload: Dict[str, Any]) -> Dict[str, Any]:
    scenario = scenario_from_payload(payload)
    algorithms: List[str] = payload.get("algorithms") or ["CBS"]
    time_limit = min(float(payload.get("time_limit", DEFAULT_TIME_LIMIT)), MAX_TIME_LIMIT)
    order = payload.get("priority_order") or "index"

    problems = _sanity_check(scenario)
    sic = sum_of_individual_costs(scenario.grid, scenario.starts, scenario.goals)

    # Naive baseline (a few milliseconds): it tells us how much coordination
    # this instance needs, and it is the same quantity the experiments record as
    # "conflicts_initial" for every algorithm.
    baseline = solve(scenario, "Independent")
    baseline_conflicts = baseline.conflicts_final

    results = []
    for algorithm in algorithms:
        if algorithm not in PLANNERS:
            results.append({"algorithm": algorithm, "status": "error", "success": False,
                            "details": {"reason": "unknown algorithm"}})
            continue
        kwargs: Dict[str, Any] = {"time_limit": time_limit}
        if algorithm == "Prioritized":
            import random

            kwargs["order"] = order
            kwargs["rng"] = random.Random(0)
        started = time.perf_counter()
        result = solve(scenario, algorithm, **kwargs)
        result.runtime_sec = time.perf_counter() - started
        if baseline_conflicts is not None and algorithm != "Independent":
            result.conflicts_initial = baseline_conflicts
        result = check_planner_result(scenario, result)
        results.append(planner_payload(scenario, result, sic))

    return {
        "results": results,
        "sic": sic,
        "problems": problems,
        "num_agents": scenario.num_agents,
    }


def _sanity_check(scenario: Scenario) -> List[str]:
    problems: List[str] = []
    grid = scenario.grid
    for i, (start, goal) in enumerate(zip(scenario.starts, scenario.goals)):
        if not grid.is_free(start):
            problems.append(f"agent {i}: start {start} is blocked")
        if not grid.is_free(goal):
            problems.append(f"agent {i}: goal {goal} is blocked")
    if len(set(scenario.starts)) != len(scenario.starts):
        problems.append("duplicate start positions")
    if len(set(scenario.goals)) != len(scenario.goals):
        problems.append("duplicate goal positions")
    return problems


class MAPFHandler(BaseHTTPRequestHandler):
    server_version = "MAPFDemo/1.0"

    # ------------------------------------------------------------------ utils
    def _send(self, code: int, payload: Any, content_type: str = "application/json") -> None:
        if isinstance(payload, (dict, list)):
            body = json.dumps(payload).encode("utf-8")
        elif isinstance(payload, str):
            body = payload.encode("utf-8")
        else:
            body = payload
        self.send_response(code)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        # Allow being embedded/queried from the preview proxy.
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()
        self.wfile.write(body)

    def _read_json(self) -> Dict[str, Any]:
        length = int(self.headers.get("Content-Length", 0) or 0)
        if not length:
            return {}
        return json.loads(self.rfile.read(length).decode("utf-8"))

    def log_message(self, fmt: str, *args: Any) -> None:  # quieter logs
        sys.stderr.write("[demo] %s - %s\n" % (self.address_string(), fmt % args))

    # -------------------------------------------------------------------- GET
    def do_GET(self) -> None:  # noqa: N802
        path = urlparse(self.path).path
        if path in ("/", "/index.html"):
            try:
                with open(os.path.join(STATIC_DIR, "index.html"), "rb") as handle:
                    self._send(200, handle.read(), "text/html; charset=utf-8")
            except OSError:
                self._send(404, {"error": "index.html not found"})
        elif path == "/api/health":
            self._send(
                200,
                {
                    "status": "ok",
                    "planners": sorted(PLANNERS),
                    "default_time_limit": DEFAULT_TIME_LIMIT,
                },
            )
        elif path == "/api/structures":
            from environment.generators import DISTRIBUTIONS, STRUCTURES

            self._send(
                200,
                {
                    "structures": list(STRUCTURES),
                    "distributions": list(DISTRIBUTIONS),
                    "planners": sorted(PLANNERS),
                },
            )
        else:
            self._send(404, {"error": f"unknown path {path}"})

    def do_OPTIONS(self) -> None:  # noqa: N802
        self.send_response(204)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.end_headers()

    # ------------------------------------------------------------------- POST
    def do_POST(self) -> None:  # noqa: N802
        path = urlparse(self.path).path
        try:
            payload = self._read_json()
            if path == "/api/generate":
                self._send(200, handle_generate(payload))
            elif path == "/api/solve":
                self._send(200, handle_solve(payload))
            else:
                self._send(404, {"error": f"unknown path {path}"})
        except Exception as exc:  # surface the error to the UI instead of dying
            import traceback

            traceback.print_exc()
            self._send(500, {"error": f"{type(exc).__name__}: {exc}"})


def main() -> None:
    parser = argparse.ArgumentParser(description="Interactive MAPF demo server")
    parser.add_argument("--host", default="0.0.0.0")
    parser.add_argument("--port", type=int, default=8000)
    args = parser.parse_args()

    server = ThreadingHTTPServer((args.host, args.port), MAPFHandler)
    print(f"MAPF demo listening on http://{args.host}:{args.port}", flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
