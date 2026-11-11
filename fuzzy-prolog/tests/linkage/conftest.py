from __future__ import annotations

import pytest

from identitylink.application.deduplicate import Deduplicator
from identitylink.domain.match import LinkageReport
from identitylink.domain.record import DateValue, PersonRecord
from identitylink.infrastructure.knowledge import (
    PackagedKnowledge,
    default_records_csv,
    default_truth_csv,
)


def _record(
    identifier: str, last: str, first: str, birth: DateValue, city: str = "", phone: str = ""
) -> PersonRecord:
    return PersonRecord(identifier, last, first, birth, city, phone)


RECORDS = [
    _record("p1", "El Amrani", "Mohamed", DateValue(1990, 5, 12), "Casablanca", "0612345678"),
    _record("p2", "Lamrani", "Mohammed", DateValue(1990, 5, 12), "Casa", "+212 6 12 34 56 78"),
    _record("p3", "Lamrani", "Muhammad", DateValue(1990)),
    _record("p4", "El Amrani", "Mohamed", DateValue(1975, 1, 3), "Rabat", "0699999999"),  # homonyme
    _record("p5", "Benjelloun", "Khadija", DateValue(1988, 2, 2), "Fes", "0611111111"),
    _record("p6", "Ben Jelloun", "Khadidja", DateValue(1988, 2, 2), "Fez", "0611111111"),
    _record("p7", "Tazi", "Sara", DateValue(2001, 9, 9), "Rabat"),
]


@pytest.fixture(scope="session")
def knowledge() -> PackagedKnowledge:
    return PackagedKnowledge()


@pytest.fixture(scope="session")
def deduplicator(knowledge: PackagedKnowledge) -> Deduplicator:
    return Deduplicator(knowledge)


@pytest.fixture(scope="session")
def small_report(deduplicator: Deduplicator) -> LinkageReport:
    return deduplicator.run(RECORDS, threshold=0.7)


@pytest.fixture(scope="session")
def sample_paths() -> tuple[str, str]:
    return str(default_records_csv()), str(default_truth_csv())
