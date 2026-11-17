import json
import math
import pytest
from agents.belief import Belief
from agents.interfaces import CellFact, Message


def packet(seq=0, send=1, arrival=3, observed=1, state="blocked", kind="MAP"):
    payload = {"cells": [dict(cell=[2, 0], state=state, observed_at=observed, origin=0)]}
    return Message(0, 1, kind, seq, send, arrival, json.dumps(payload))


def test_duplicate_reorder_and_age_use_generation_time():
    b = Belief(1)
    assert math.isinf(b.age(0, "MAP", 0))
    assert b.receive(packet(seq=2), 3)
    assert not b.receive(packet(seq=1), 3)
    assert not b.receive(packet(seq=2), 3)
    assert b.age(0, "MAP", 4) == 3
    assert b.cells[(2, 0)].origin == 0


def test_new_transport_sequence_cannot_overwrite_newer_direct_fact():
    b = Belief(1)
    b.update(CellFact((2, 0), "free", 5, 1))
    b.receive(packet(seq=5, send=6, arrival=7, observed=1), 7)
    assert b.state((2, 0)) == "free"
    assert b.disagreements  # explicit disagreement; no true-map consultation


@pytest.mark.parametrize("msg,now", [(packet(), 2), (packet(send=4), 4),
                                   (packet(observed=2), 3)])
def test_future_or_premature_data_rejected_atomically(msg, now):
    b = Belief(1)
    with pytest.raises(ValueError):
        b.receive(msg, now)
    assert not b.cells and not b.latest
