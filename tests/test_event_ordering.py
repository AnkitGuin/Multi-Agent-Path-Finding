import math
import random
import pytest
from simulation.events import EventQueue, Phase


def test_ties_finish_before_sense_and_decide():
    q = EventQueue()
    for p in (Phase.DECIDE, Phase.SENSE, Phase.FINISH, Phase.DELIVER):
        q.schedule(2, p, p.name)
    assert [q.pop().kind for _ in range(4)] == ["FINISH", "DELIVER", "SENSE", "DECIDE"]


def test_zero_delay_delivery_cannot_precede_its_send():
    q = EventQueue()
    q.schedule(0, Phase.DECIDE, "SEND")
    send = q.pop()
    q.schedule(0, Phase.DELIVER, "DELIVER")
    delivery = q.pop()
    assert delivery.time == send.time and delivery.cycle > send.cycle


@pytest.mark.parametrize("bad", [-1, math.nan, math.inf])
def test_reject_invalid_times(bad):
    with pytest.raises(ValueError):
        EventQueue().schedule(bad, Phase.SENSE, "bad")


@pytest.mark.parametrize("seed", range(10))
def test_seeded_queue_is_totally_ordered(seed):
    q, rng = EventQueue(), random.Random(seed)
    for _ in range(100):
        q.schedule(rng.randrange(4)/2, rng.choice(list(Phase)), "event")
    events = [q.pop() for _ in range(100)]
    assert events == sorted(events)
    with pytest.raises(ValueError):
        q.schedule(0, Phase.SENSE, "past")
