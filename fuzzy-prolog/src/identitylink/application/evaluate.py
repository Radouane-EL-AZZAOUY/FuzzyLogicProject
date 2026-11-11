"""Use case: measure a linkage report against a ground truth (precision, recall, F1)."""

from __future__ import annotations

from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass
from itertools import combinations

from identitylink.domain.match import LinkageReport


@dataclass(frozen=True, slots=True)
class Metrics:
    threshold: float
    true_positives: int
    false_positives: int
    false_negatives: int

    @property
    def precision(self) -> float:
        total = self.true_positives + self.false_positives
        return self.true_positives / total if total else 1.0

    @property
    def recall(self) -> float:
        total = self.true_positives + self.false_negatives
        return self.true_positives / total if total else 1.0

    @property
    def f1(self) -> float:
        p, r = self.precision, self.recall
        return 2 * p * r / (p + r) if (p + r) else 0.0


def truth_pairs(person_of: Mapping[str, str]) -> set[tuple[str, str]]:
    """Every unordered pair of records describing the same person, as (min, max)."""
    groups: dict[str, list[str]] = {}
    for record_id, person_id in person_of.items():
        groups.setdefault(person_id, []).append(record_id)
    pairs: set[tuple[str, str]] = set()
    for members in groups.values():
        for a, b in combinations(sorted(members), 2):
            pairs.add((a, b))
    return pairs


def evaluate(
    report: LinkageReport, truth: set[tuple[str, str]], threshold: float | None = None
) -> Metrics:
    threshold = report.threshold if threshold is None else threshold
    predicted = {c.pair for c in report.candidates if c.degree >= threshold}
    tp = len(predicted & truth)
    return Metrics(threshold, tp, len(predicted - truth), len(truth - predicted))


def sweep(
    report: LinkageReport, truth: set[tuple[str, str]], thresholds: Iterable[float]
) -> Sequence[Metrics]:
    return [evaluate(report, truth, t) for t in thresholds]


def false_pairs(
    report: LinkageReport, truth: set[tuple[str, str]]
) -> tuple[list[tuple[str, str]], list[tuple[str, str]]]:
    """(false positives, false negatives) at the report's threshold, for error analysis."""
    predicted = report.matched_pairs
    return sorted(predicted - truth), sorted(truth - predicted)
