"""Immutable information boundary for decentralized execution.

Only observations, delivered messages, own goal and geometric bounds cross
this boundary. Coordinates are (column, row). Times are simulation seconds.
"""
from dataclasses import asdict, dataclass
import json
from typing import Literal, Protocol

Cell = tuple[int, int]


@dataclass(frozen=True)
class CellFact:
    cell: Cell
    state: Literal["free", "blocked"]
    observed_at: float
    origin: int


@dataclass(frozen=True)
class VisibleAgent:
    agent_id: int
    occupied_cells: tuple[Cell, ...]
    moving: bool


@dataclass(frozen=True)
class Observation:
    ego_id: int
    event_time: float
    ego_pose: Cell
    visible_cells: tuple[CellFact, ...]
    visible_agents: tuple[VisibleAgent, ...] = ()
    sensor_radius: int = 1
    occlusion_model: str = "none"


@dataclass(frozen=True)
class Message:
    sender: int
    recipient: int
    kind: str
    sequence_id: int
    send_time: float
    deliver_time: float
    payload_json: str

    def wire_bytes(self) -> bytes:
        # Delivery time is transport metadata, not transmitted knowledge.
        data = asdict(self)
        del data["deliver_time"]
        return json.dumps(data, sort_keys=True, separators=(",", ":"),
                          ensure_ascii=True, allow_nan=False).encode("utf-8")

    @property
    def byte_count(self) -> int:
        return len(self.wire_bytes())


@dataclass(frozen=True)
class OutgoingMessage:
    recipient: int
    kind: str
    payload_json: str


@dataclass(frozen=True)
class AgentDecision:
    action_kind: Literal["move", "wait"]
    next_vertex: Cell | None = None
    messages: tuple[OutgoingMessage, ...] = ()


class LocalPolicy(Protocol):
    def decide(self, observation: Observation,
               messages: tuple[Message, ...]) -> AgentDecision: ...
