"""Fail-closed pairwise move claims; a standard protocol adaptation, not novelty.

Local promises never expire: each grant excludes conflicting own/other claims
until explicit RELEASE for that epoch. Tombstones reject reordered old requests.
This implementation does not provide priority inheritance, deadlock-freedom,
Byzantine protection, or an unconditional distributed safety theorem.
"""
from dataclasses import dataclass, field
import json
from .interfaces import Cell, OutgoingMessage


@dataclass
class Claim:
    epoch: int
    source: Cell
    target: Cell
    peers: set[int] = field(default_factory=set)
    grants: set[int] = field(default_factory=set)
    committed: bool = False

    @property
    def resources(self):
        return frozenset((self.source, self.target))


class Claims:
    def __init__(self, ego_id):
        self.ego_id = ego_id
        self.epoch = 0
        self.own: Claim | None = None
        self.promises: dict[tuple[int, int], frozenset[Cell]] = {}
        self.released: dict[int, int] = {}
        self.awaiting_ack: set[tuple[int, int]] = set()

    def packet(self, peer, kind, epoch, **payload):
        return OutgoingMessage(peer, kind, json.dumps(dict(epoch=epoch, **payload),
                                                      sort_keys=True, separators=(",", ":")))

    def cancel(self):
        if self.own is not None:
            if self.own.committed:
                raise ValueError("cannot cancel a move before physical completion")
            self.awaiting_ack.update((p, self.own.epoch) for p in self.own.peers)
            self.own = None

    def completed(self, pose):
        if self.own is not None and self.own.committed:
            if pose != self.own.target:
                raise ValueError("committed move has not physically completed")
            self.awaiting_ack.update((p, self.own.epoch) for p in self.own.peers)
            self.own = None

    def receive(self, msg, pose):
        if msg.kind not in {"REQUEST", "GRANT", "REJECT", "RELEASE", "ACK"}:
            return []
        data = json.loads(msg.payload_json)
        epoch, peer = data["epoch"], msg.sender
        if not isinstance(epoch, int) or epoch < 1:
            raise ValueError("invalid claim epoch")
        key = (peer, epoch)
        if msg.kind == "RELEASE":
            self.released[peer] = max(epoch, self.released.get(peer, 0))
            # An epoch fences all older requests by this cooperating agent.
            for old in list(self.promises):
                if old[0] == peer and old[1] <= epoch:
                    del self.promises[old]
            return [self.packet(peer, "ACK", epoch)]
        if msg.kind == "ACK":
            self.awaiting_ack.discard(key)
            return []
        if msg.kind in {"GRANT", "REJECT"}:
            if self.own is not None and self.own.epoch == epoch and peer in self.own.peers:
                if msg.kind == "GRANT":
                    self.own.grants.add(peer)
                # A reordered rejection cannot retract a nonexpiring grant.
            return []
        source, target = tuple(data["source"]), tuple(data["target"])
        if len(source) != 2 or len(target) != 2 or sum(abs(a-b) for a, b in zip(source, target)) != 1:
            raise ValueError("request must describe a neighboring move")
        resources = frozenset((source, target))
        if epoch <= self.released.get(peer, 0):
            return [self.packet(peer, "REJECT", epoch)]
        if key in self.promises:
            if self.promises[key] != resources:
                raise ValueError("claim epoch reused for different resources")
            return [self.packet(peer, "GRANT", epoch)]
        conflict = pose in resources or any(resources & held for held in self.promises.values())
        if self.own is not None and self.own.resources & resources:
            if self.own.committed or self.ego_id < peer:
                conflict = True
            elif not conflict:
                self.cancel()  # fixed priority; canceled grants cannot be reused
        if conflict:
            return [self.packet(peer, "REJECT", epoch)]
        self.promises[key] = resources
        return [self.packet(peer, "GRANT", epoch)]

    def propose(self, source, target, peers):
        if self.own is None:
            self.epoch += 1
            self.own = Claim(self.epoch, source, target)
        if self.own.source != source or self.own.target != target:
            raise ValueError("release old claim before proposing a new route")
        self.own.peers.update(peers)
        return [self.packet(p, "REQUEST", self.own.epoch, source=source, target=target)
                for p in sorted(self.own.peers - self.own.grants)]

    def can_commit(self):
        return self.own is not None and self.own.peers <= self.own.grants

    def release_retries(self):
        return [self.packet(p, "RELEASE", epoch) for p, epoch in sorted(self.awaiting_ack)]
