"""Linkage results: graded candidate pairs and duplicate groups."""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass, field

from fuzzyprolog import Solution
from identitylink.domain.record import PersonRecord


@dataclass(frozen=True, slots=True)
class MatchCandidate:
    left: PersonRecord
    right: PersonRecord
    degree: float
    proof: Solution
    """The best derivation of ``meme_personne(left, right)`` (for explanations)."""

    @property
    def rule(self) -> str:
        """Text of the decision clause that produced the best derivation."""
        return self.proof.steps[0].via if self.proof.steps else ""

    @property
    def pair(self) -> tuple[str, str]:
        return (self.left.identifier, self.right.identifier)


@dataclass(frozen=True, slots=True)
class DuplicateGroup:
    members: tuple[PersonRecord, ...]
    """Records believed to describe one person (connected by matches ≥ threshold)."""

    @property
    def identifiers(self) -> tuple[str, ...]:
        return tuple(m.identifier for m in self.members)


@dataclass(frozen=True, slots=True)
class LinkageReport:
    threshold: float
    candidates: tuple[MatchCandidate, ...]
    """Every pair with a degree above the λ-cut, strongest first."""
    groups: tuple[DuplicateGroup, ...] = field(default_factory=tuple)
    """Groups formed by the pairs whose degree reaches ``threshold``."""
    records: int = 0
    seconds: float = 0.0

    @property
    def matches(self) -> tuple[MatchCandidate, ...]:
        return tuple(c for c in self.candidates if c.degree >= self.threshold)

    @property
    def matched_pairs(self) -> set[tuple[str, str]]:
        return {c.pair for c in self.matches}


def cluster(
    records: Iterable[PersonRecord], pairs: Iterable[tuple[str, str]]
) -> tuple[DuplicateGroup, ...]:
    """Union-find over matched pairs; returns groups of size ≥ 2, largest first."""
    by_id = {r.identifier: r for r in records}
    parent: dict[str, str] = {identifier: identifier for identifier in by_id}

    def find(x: str) -> str:
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x

    for a, b in pairs:
        if a in parent and b in parent:
            ra, rb = find(a), find(b)
            if ra != rb:
                parent[max(ra, rb)] = min(ra, rb)
    members: dict[str, list[PersonRecord]] = {}
    for identifier, record in by_id.items():
        members.setdefault(find(identifier), []).append(record)
    groups = [
        DuplicateGroup(tuple(sorted(group, key=lambda r: r.identifier)))
        for group in members.values()
        if len(group) >= 2
    ]
    groups.sort(key=lambda g: (-len(g.members), g.identifiers))
    return tuple(groups)
