"""Paired local baseline runner. No oracle information enters local factories."""
from baselines.local_independent import IndependentLocal
from baselines.local_reservation import LocalReservation
from simulation.communication import NetworkConfig
from simulation.episode import EpisodeConfig, digest, run_episode
from .scenario_registry import build_scenario


METHODS = ("local_independent", "observed_yield", "claims_periodic", "claims_always",
           "claims_selective", "claims_no_map", "claims_full_replan")


def make_policy(method, i, goal, width, height, settings):
    if method == "local_independent":
        return IndependentLocal(i, goal, width, height)
    if method == "observed_yield":
        return IndependentLocal(i, goal, width, height, observed_yield=True, broadcast_period=2)
    control = {"claims_periodic": "periodic", "claims_always": "always",
               "claims_selective": "selective", "claims_no_map": "none",
               "claims_full_replan": "selective"}[method]
    return LocalReservation(i, goal, width, height, communication=control,
                            period=settings.get("broadcast_period", 2),
                            freshness=settings.get("freshness", 4),
                            incremental=method != "claims_full_replan")


def run_case(method, family, seed, agents, size, fault, settings):
    scenario = build_scenario(family, seed, agents, size)
    n = scenario.num_agents
    config = EpisodeConfig(horizon=settings["horizon"], sensor_radius=settings["sensor_radius"],
                           durations=tuple(1+(i % 3)*.25 for i in range(n)),
                           duration_seed=seed+200000, duration_jitter=fault["jitter"],
                           wait_duration=settings.get("wait_duration", .5),
                           network=NetworkConfig(seed=seed+300000, radius=settings["network_radius"],
                                                 max_latency=fault["latency"], loss=fault["loss"],
                                                 duplication=fault.get("duplication", 0)))
    policies = tuple(make_policy(method, i, goal, scenario.grid.width, scenario.grid.height, settings)
                     for i, goal in enumerate(scenario.goals))
    row = run_episode(scenario, policies, config, method=method)
    row.update(map_family=family, scenario_seed=seed, duration_seed=config.duration_seed,
               message_seed=config.network.seed, fault=fault["name"],
               sensor_radius=config.sensor_radius, network_radius=config.network.radius,
               observed_obstacle_density=scenario.grid.obstacle_density,
               initial_unknown_fraction=sum(1-sum(abs(x-s[0])+abs(y-s[1]) <= config.sensor_radius
                   for x in range(scenario.grid.width) for y in range(scenario.grid.height)) / scenario.grid.size
                   for s in scenario.starts)/n,
               pair_id=digest(dict(scenario=scenario.to_dict(), config=config)),
               study_status="development_only_no_novelty_claim")
    row["baseline_version"] = "local-controls-v0.1"
    row["run_id"] = digest(dict(pair=row["pair_id"], method=method, settings=settings,
                                model=row["model"], baseline=row["baseline_version"]))
    return row
