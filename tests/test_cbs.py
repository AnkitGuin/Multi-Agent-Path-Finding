"""CBS tests, including an exhaustive optimality cross-check.

The strongest test here compares CBS against a brute-force joint-state Dijkstra
on tiny instances.  Brute force enumerates the full joint configuration space,
so its cost *is* the optimum by construction -- if CBS matches it on many random
instances, the two-level search is behaving as the theory predicts.
"""

import heapq
import itertools
import random
from math import inf

import pytest

from environment.generators import generate_grid, generate_scenario
from environment.grid import GridMap
from planning.cbs import solve_cbs
from planning.common import STATUS_NO_SOLUTION, STATUS_OK
from evaluation.metrics import sum_of_individual_costs, validate_solution

ALCOVE = GridMap.from_ascii("...\n@.@")
ALCOVE_STARTS = [(0, 0), (2, 0)]
ALCOVE_GOALS = [(2, 0), (0, 0)]


def brute_force_optimal_soc(grid, starts, goals, max_states=400000):
    """Exhaustive Dijkstra over joint configurations.  Returns optimal SOC/None.

    Model matches the planners exactly: an agent freezes on its goal the first
    time it reaches it ("stay at target"), each non-frozen agent performs one
    action per timestep and pays 1, vertex and edge conflicts are forbidden.
    """
    n = len(starts)
    start_state = tuple(starts)
    dist = {start_state: 0}
    heap = [(0, start_state)]
    seen = 0
    while heap:
        d, state = heapq.heappop(heap)
        if d > dist.get(state, inf):
            continue
        if all(state[i] == goals[i] for i in range(n)):
            return d
        seen += 1
        if seen > max_states:
            return None
        options = []
        for i in range(n):
            if state[i] == goals[i]:
                options.append((state[i],))  # frozen at the goal
            else:
                options.append(tuple(grid.neighbors(state[i])))
        moving = sum(1 for i in range(n) if state[i] != goals[i])
        for combo in itertools.product(*options):
            if len(set(combo)) != n:  # vertex conflict
                continue
            swap = any(
                combo[i] == state[j] and combo[j] == state[i]
                for i in range(n)
                for j in range(i + 1, n)
            )
            if swap:  # edge conflict
                continue
            nd = d + moving
            if nd < dist.get(combo, inf):
                dist[combo] = nd
                heapq.heappush(heap, (nd, combo))
    return None  # unsolvable


def test_cbs_solves_the_alcove_instance_optimally():
    result = solve_cbs(ALCOVE, ALCOVE_STARTS, ALCOVE_GOALS)
    assert result.success and result.status == STATUS_OK
    assert result.soc == 7, "optimal solution costs 4 + 3 (one agent uses the alcove)"
    assert validate_solution(ALCOVE, ALCOVE_STARTS, ALCOVE_GOALS, result.paths).valid
    # brute force must agree
    assert brute_force_optimal_soc(ALCOVE, ALCOVE_STARTS, ALCOVE_GOALS) == result.soc


def test_cbs_does_not_return_a_wrong_answer_on_an_unsolvable_instance():
    """Two agents must swap ends of a three-cell corridor: impossible.

    Note (documented limitation, see the report): on an unsolvable instance the
    CBS constraint tree is *infinite* -- every repaired plan runs into a new
    conflict later in time -- so CBS cannot prove unsolvability by exhausting
    the tree.  What it must never do is return an invalid plan, so we cap the
    search and assert that it reports failure rather than a bogus solution.
    """
    corridor = GridMap.from_ascii("...")
    starts = [(0, 0), (2, 0)]
    goals = [(2, 0), (0, 0)]
    assert brute_force_optimal_soc(corridor, starts, goals) is None
    result = solve_cbs(corridor, starts, goals, max_high_level_expansions=2000)
    assert result.success is False
    assert result.status in (STATUS_NO_SOLUTION, "timeout")
    assert result.paths == []  # no plan is returned when CBS did not succeed


def test_cbs_reports_no_solution_when_a_goal_is_statically_unreachable():
    grid = GridMap.from_ascii("..@..")
    result = solve_cbs(grid, [(0, 0), (4, 0)], [(4, 0), (0, 0)])
    assert result.success is False
    assert result.status == STATUS_NO_SOLUTION
    assert "unreachable" in result.details["reason"]


def test_cbs_with_one_agent_equals_astar():
    scenario = generate_scenario(16, 16, 1, 0.25, "random", "uniform", seed=4)
    result = solve_cbs(scenario.grid, scenario.starts, scenario.goals)
    assert result.success
    sic = sum_of_individual_costs(scenario.grid, scenario.starts, scenario.goals)
    assert result.soc == sic


@pytest.mark.parametrize("seed", range(12))
def test_cbs_is_optimal_against_brute_force_two_agents(seed):
    grid = generate_grid(5, 5, 0.2, "random", rng=random.Random(seed))
    free = grid.free_cells
    rng = random.Random(seed + 500)
    starts = rng.sample(free, 2)
    goals = rng.sample([c for c in free if c not in starts], 2)

    expected = brute_force_optimal_soc(grid, starts, goals)
    result = solve_cbs(grid, starts, goals)
    if expected is None:
        assert not result.success
        assert result.status == STATUS_NO_SOLUTION
    else:
        assert result.success, f"seed {seed}: CBS failed on a solvable instance"
        assert result.soc == expected, f"seed {seed}: CBS SOC {result.soc} != optimal {expected}"
        assert validate_solution(grid, starts, goals, result.paths).valid


@pytest.mark.parametrize("seed", range(4))
def test_cbs_is_optimal_against_brute_force_three_agents(seed):
    grid = generate_grid(4, 4, 0.15, "random", rng=random.Random(seed))
    free = grid.free_cells
    if len(free) < 6:
        pytest.skip("map too small")
    rng = random.Random(seed + 900)
    starts = rng.sample(free, 3)
    goals = rng.sample([c for c in free if c not in starts], 3)

    expected = brute_force_optimal_soc(grid, starts, goals)
    result = solve_cbs(grid, starts, goals)
    if expected is None:
        assert not result.success
    else:
        assert result.success
        assert result.soc == expected
        assert validate_solution(grid, starts, goals, result.paths).valid


def test_cbs_tie_break_does_not_change_the_cost():
    scenario = generate_scenario(12, 12, 5, 0.2, "random", "uniform", seed=13)
    plain = solve_cbs(scenario.grid, scenario.starts, scenario.goals, tie_break=False)
    tie = solve_cbs(scenario.grid, scenario.starts, scenario.goals, tie_break=True)
    if plain.success and tie.success:
        assert plain.soc == tie.soc
        assert validate_solution(scenario.grid, scenario.starts, scenario.goals, tie.paths).valid


def test_cbs_reports_timeout_instead_of_a_wrong_answer():
    scenario = generate_scenario(20, 20, 25, 0.1, "random", "uniform", seed=17)
    result = solve_cbs(
        scenario.grid, scenario.starts, scenario.goals, time_limit=0.001
    )
    assert result.status in (STATUS_OK, "timeout")
    if result.status == "timeout":
        assert result.success is False
        assert result.paths == []


def test_cbs_handles_agents_that_need_to_wait_for_each_other():
    # Two agents in a single corridor going the same way: the follower waits.
    grid = GridMap.from_ascii(".....")
    starts = [(0, 0), (1, 0)]
    goals = [(3, 0), (4, 0)]
    result = solve_cbs(grid, starts, goals)
    assert result.success
    assert validate_solution(grid, starts, goals, result.paths).valid
    assert result.soc == 3 + 3  # the follower cannot overtake
