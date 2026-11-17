from scripts.analyze_async import bootstrap_clusters, wilson


def test_wilson_retains_uncertainty_for_zero_and_all_success():
    lo, hi = wilson(0, 10)
    assert abs(lo) < 1e-12 and 0 < hi < 1
    lo, hi = wilson(10, 10)
    assert 0 < lo < 1 and abs(hi-1) < 1e-12


def test_bootstrap_resamples_maps_and_does_not_invent_one_map_interval():
    assert bootstrap_clusters([("one", 3), ("one", 5)]) == (4, None, None, 1)
    result = bootstrap_clusters([("one", 3), ("two", 5)])
    assert result == bootstrap_clusters([("one", 3), ("two", 5)])
    assert result[0] == 4 and result[-1] == 2 and result[1] <= 4 <= result[2]
