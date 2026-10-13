"""Ports: the interfaces the domain needs the outside world to implement.

Concrete adapters live in :mod:`fuzzyscout.infrastructure`; the application layer only
ever depends on these protocols (dependency-inversion principle).
"""

from __future__ import annotations

from collections.abc import Sequence
from typing import Protocol

from fuzzyengine import FuzzyPipeline
from fuzzyscout.domain.player import Player
from fuzzyscout.domain.position import Position


class PlayerRepository(Protocol):
    def all(self) -> Sequence[Player]: ...

    def get(self, identifier: str) -> Player:
        """Return the player or raise :class:`PlayerNotFoundError`."""
        ...


class PositionCatalog(Protocol):
    def all(self) -> Sequence[Position]: ...

    def get(self, code: str) -> Position:
        """Return the position or raise :class:`PositionNotFoundError`."""
        ...


class PipelineProvider(Protocol):
    def pipeline_for(self, position: Position) -> FuzzyPipeline:
        """Build (or fetch from cache) the inference pipeline of ``position``."""
        ...
