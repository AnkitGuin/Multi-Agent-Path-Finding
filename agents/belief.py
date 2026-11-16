"""Static-map facts and freshness memory with explicit provenance.

No world or legacy BFS can be accessed through this object. Unknown cells are
absent, never silently marked verified free. Transport sequence IDs do not
overwrite newer cell observations.
"""
import json
import math
from .interfaces import Cell, CellFact, Message, Observation


class Belief:
    def __init__(self, ego_id: int):
        self.ego_id = ego_id
        self.cells: dict[Cell, CellFact] = {}
        self.latest: dict[tuple[int, str], Message] = {}
        self.disagreements: list[tuple[CellFact, CellFact]] = []

    def update(self, fact: CellFact):
        if (fact.state not in ("free", "blocked") or not math.isfinite(fact.observed_at)
                or fact.observed_at < 0 or len(fact.cell) != 2
                or not all(isinstance(v, int) for v in fact.cell)):
            raise ValueError("invalid map fact")
        old = self.cells.get(fact.cell)
        if old and old.state != fact.state:
            self.disagreements.append((old, fact))
        if old is None or (fact.observed_at, -fact.origin) > (old.observed_at, -old.origin):
            self.cells[fact.cell] = fact

    def observe(self, observation: Observation):
        if observation.ego_id != self.ego_id:
            raise ValueError("observation belongs to another agent")
        for fact in observation.visible_cells:
            if fact.observed_at > observation.event_time:
                raise ValueError("future observation")
            self.update(fact)

    def receive(self, msg: Message, now: float) -> bool:
        if (not all(math.isfinite(v) for v in (msg.send_time, msg.deliver_time, now))
                or msg.send_time < 0 or msg.recipient != self.ego_id or msg.deliver_time > now
                or msg.send_time > msg.deliver_time or msg.sequence_id < 0):
            raise ValueError("invalid message envelope or premature delivery")
        key = (msg.sender, msg.kind)
        old = self.latest.get(key)
        if old is not None and msg.sequence_id <= old.sequence_id:
            return False
        facts = []
        if msg.kind == "MAP":
            for raw in json.loads(msg.payload_json).get("cells", []):
                fact = CellFact(tuple(raw["cell"]), raw["state"],
                                raw["observed_at"], raw["origin"])
                if fact.observed_at > msg.send_time:
                    raise ValueError("fact was generated after message send")
                if (fact.state not in ("free", "blocked") or not math.isfinite(fact.observed_at)
                        or fact.observed_at < 0 or len(fact.cell) != 2
                        or not all(isinstance(v, int) for v in fact.cell)):
                    raise ValueError("invalid communicated fact")
                facts.append(fact)
        # Validate entire message before committing state.
        for fact in facts:
            self.update(fact)
        self.latest[key] = msg
        return True

    def age(self, sender: int, kind: str, now: float) -> float:
        msg = self.latest.get((sender, kind))
        return math.inf if msg is None else now - msg.send_time

    def state(self, cell: Cell) -> str:
        fact = self.cells.get(cell)
        return fact.state if fact else "unknown"
