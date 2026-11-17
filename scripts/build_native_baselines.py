"""Build downloaded authors' C++ sources and preserve success/failure evidence.

Checkouts under external/ are intentionally not redistributed. Source files
remain unmodified. A force-included header supplies only map-directory macros.
"""
import argparse
import hashlib
import json
from pathlib import Path
import shutil
import subprocess

ROOT = Path(__file__).resolve().parents[1]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=Path, default=ROOT/"research/reports/native_build")
    args = parser.parse_args()
    args.out.mkdir(parents=True, exist_ok=True)
    compiler = shutil.which("g++")
    if compiler is None:
        raise SystemExit("g++ missing; install a C++17 compiler")
    records = []
    causal = ROOT/"external/time-independent-planning"
    header = causal/"research_paths.hpp"
    header.write_text('#define _MAPDIR_ "'+(causal/"map").as_posix()+'/"\n'
                      '#define _PLANDIR_ "'+(causal/"mapf_plan").as_posix()+'/"\n', encoding="utf-8")
    graph = causal/"third_party/grid-pathfinding/graph"
    sources = sorted((causal/"time_independent/src").glob("*.cpp")) + sorted((graph/"src").glob("*.cpp"))
    cmd = [compiler, "-std=c++1z", "-O1", "-include", str(header),
           "-I", str(causal/"time_independent/include"), "-I", str(graph/"include"),
           *map(str, sources), str(causal/"app.cpp"), "-o", str(causal/"app.exe")]
    lsrp = ROOT/"external/lsrp"
    lsrc = [p for p in sorted((lsrp/"source").glob("*.cpp")) if p.name != "main.cpp"]
    commands = [("causal_pibt", causal, cmd), ("lsrp", lsrp,
                [compiler, "-std=c++1z", "-O1", "-I", str(lsrp/"include"),
                 *map(str, lsrc), str(lsrp/"test/test_toyexample.cpp"), "-o", str(lsrp/"toy.exe")])]
    for name, checkout, command in commands:
        result = subprocess.run(command, cwd=ROOT, capture_output=True, text=True, timeout=300)
        (args.out/f"{name}.txt").write_text(result.stdout+result.stderr, encoding="utf-8")
        revision = subprocess.check_output(["git", "-c", f"safe.directory={checkout.as_posix()}",
                                            "-C", str(checkout), "rev-parse", "HEAD"], text=True).strip()
        records.append(dict(name=name, revision=revision, command=command, exit_code=result.returncode,
                            log=f"{name}.txt", source_modified=False))
        print(f"{name}: exit {result.returncode}", flush=True)
    (args.out/"manifest.json").write_text(json.dumps(dict(compiler=subprocess.check_output(
        [compiler, "--version"], text=True), builds=records), indent=2), encoding="utf-8")


if __name__ == "__main__":
    main()
