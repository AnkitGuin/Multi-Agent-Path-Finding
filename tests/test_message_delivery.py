import pytest
from simulation.communication import Network, NetworkConfig
from simulation.events import EventQueue


def test_total_loss_counts_actual_serialized_transmission_bytes():
    q = EventQueue()
    n = Network(q, NetworkConfig(loss=1))
    msg = n.send(0, 1, "MAP", {"cells": []}, (0, 0), (1, 0))
    assert n.messages_sent == 1 and n.bytes_sent == len(msg.wire_bytes())
    assert not q and n.messages_delivered == n.bytes_delivered == 0


def test_range_and_zero_latency_duplicates():
    q = EventQueue()
    n = Network(q, NetworkConfig(radius=1, duplication=1))
    assert n.send(0, 1, "MAP", {}, (0, 0), (2, 0)) is None
    assert n.messages_sent == 0
    msg = n.send(0, 1, "MAP", {}, (0, 0), (1, 0))
    events = [q.pop(), q.pop()]
    assert all(e.payload.sequence_id == msg.sequence_id for e in events)
    for e in events:
        n.delivered(e.payload)
    assert n.messages_delivered == 2
    assert n.bytes_delivered == 2 * n.bytes_sent


def test_random_delay_can_reorder_and_is_independent_of_other_senders():
    def packets(extra=False):
        q = EventQueue()
        net = Network(q, NetworkConfig(seed=4, radius=None, max_latency=10))
        result = []
        for i in range(20):
            if extra:
                net.send(7, 8, "MAP", {}, (0, 0), (0, 0))
            result.append(net.send(0, 1, "MAP", {"i": i}, (0, 0), (0, 0)))
        return result
    a, b = packets(), packets(True)
    assert a == b
    assert sorted(a, key=lambda m: m.deliver_time) != a


@pytest.mark.parametrize("kwargs", [{"loss": -0.1}, {"loss": 2},
                                     {"min_latency": 2, "max_latency": 1},
                                     {"max_latency": float("nan")}, {"radius": -1}])
def test_invalid_network_config(kwargs):
    with pytest.raises(ValueError):
        NetworkConfig(**kwargs)
