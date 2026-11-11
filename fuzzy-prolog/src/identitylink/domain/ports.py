"""Ports implemented by the infrastructure layer."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Protocol

from identitylink.domain.record import PersonRecord


class RecordRepository(Protocol):
    def all(self) -> Sequence[PersonRecord]: ...


class KnowledgeSource(Protocol):
    """Provides the Prolog texts of the linkage rules and of the similarity declarations."""

    def rules(self) -> str: ...

    def similarities(self) -> str: ...


class GroundTruth(Protocol):
    """Maps a record identifier to the identifier of the real person it describes."""

    def person_of(self) -> Mapping[str, str]: ...
