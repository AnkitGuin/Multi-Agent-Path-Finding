"""Seeded local transport with loss, latency, duplicates and serialized bytes.

Randomness is keyed by directed logical-message ID so another sender's traffic
cannot change this message's loss/delay. Counterfactual methods with different
message contents have no promised packet-level coupling.
"""
from dataclasses import dataclass, replace
import hashlib
import json
import math
import random
from agents.interfaces import Cell, Message
from .events import EventQueue, Phase


@dataclass(frozen=True)
class NetworkConfig:
    seed: int = 0
    radius: int | None = 3
    min_latency: float = 0.0
    max_latency: float = 0.0
    loss: float = 0.0
    duplication: float = 0.0

    def __post_init__(self):
        if (self.radius is not None and (isinstance(self.radius, bool) or not isinstance(self.radius, int)
                                         or self.radius < 0)):
            raise ValueError("radius must be nonnegative or None for all-to-all")
        if (not all(math.isfinite(v) for v in (self.min_latency, self.max_latency,
                                              self.loss, self.duplication))
                or not 0 <= self.loss <= 1 or not 0 <= self.duplication <= 1
                or not 0 <= self.min_latency <= self.max_latency):
            raise ValueError("invalid network distribution")


class Network:
    def __init__(self, queue: EventQueue, config: NetworkConfig):
        self.queue, self.config = queue, config
        self.messages_sent = self.messages_delivered = 0
        self.bytes_sent = self.bytes_delivered = 0
        self.trace: list[dict] = []
        self._sequences: dict[tuple[int, int, str], int] = {}

    def send(self, sender: int, recipient: int, kind: str, payload: dict,
             sender_pose: Cell, recipient_pose: Cell) -> Message | None:
        c = self.config
        distance = sum(abs(a-b) for a, b in zip(sender_pose, recipient_pose))
        if c.radius is not None and distance > c.radius:
            self.trace.append(dict(event="out_of_range", time=self.queue.now,
                                   sender=sender, recipient=recipient))
            return None
        key = (sender, recipient, kind)
        seq = self._sequences.get(key, 0)
        self._sequences[key] = seq + 1
        seed = hashlib.sha256(f"{c.seed}:{sender}:{recipient}:{kind}:{seq}".encode()).digest()
        rng = random.Random(int.from_bytes(seed, "big"))
        lost = rng.random() < c.loss
        arrival = self.queue.now + rng.uniform(c.min_latency, c.max_latency)
        msg = Message(sender, recipient, kind, seq, self.queue.now, arrival,
                      json.dumps(payload, sort_keys=True, separators=(",", ":"),
                                 allow_nan=False))
        self.messages_sent += 1
        self.bytes_sent += msg.byte_count
        self.trace.append(dict(event="lost" if lost else "sent", message=msg))
        if not lost:
            self.queue.schedule(arrival, Phase.DELIVER, "MESSAGE_DELIVER", msg)
            if rng.random() < c.duplication:
                duplicate = replace(msg, deliver_time=arrival + rng.uniform(0, c.max_latency))
                self.queue.schedule(duplicate.deliver_time, Phase.DELIVER,
                                    "MESSAGE_DELIVER", duplicate)
                self.trace.append(dict(event="duplicated", message=duplicate))
        return msg

    def delivered(self, msg: Message):
        self.messages_delivered += 1
        self.bytes_delivered += msg.byte_count
        self.trace.append(dict(event="delivered", message=msg))
