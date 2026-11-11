"""The « commande Scout » read models: a level from 1 to 6 for one player or a squad.

Unlike the per-position aptitude, this system does not start from measured numbers
only: every input is an *observation* that may be precise, an interval or a category
(see :mod:`fuzzyengine.observations`).
"""

from __future__ import annotations

import math
from collections.abc import Mapping
from dataclasses import dataclass

from fuzzyengine import Observation, PipelineResult
from fuzzyscout.domain.evaluation import SkippedPlayer
from fuzzyscout.domain.player import Player
from fuzzyscout.domain.position import Position

LOWEST_LEVEL = 1
HIGHEST_LEVEL = 6


@dataclass(frozen=True, slots=True)
class CommandEvaluation:
    player: Player
    observations: Mapping[str, Observation]
    """The observations the system was run on (only those it requires)."""
    result: PipelineResult
    final_output: str
    """Name of the pipeline output holding the level (``niveau``)."""

    @property
    def level_value(self) -> float:
        """Defuzzified level, a real number between 1 and 6 (used to rank players)."""
        return self.result.outputs[self.final_output]

    @property
    def level(self) -> int:
        """The level itself: the nearest whole level, from 1 to 6."""
        nearest = math.floor(self.level_value + 0.5)
        return min(HIGHEST_LEVEL, max(LOWEST_LEVEL, nearest))

    @property
    def deduced(self) -> dict[str, float]:
        """Score of every deduced linguistic variable (``vitesse``, ``acceleration``...)."""
        return {k: v for k, v in self.result.outputs.items() if k != self.final_output}

    @property
    def labels(self) -> dict[str, str]:
        return dict(self.result.labels)

    @property
    def conclusions(self) -> dict[str, dict[str, float]]:
        """Degree of each term of every output, as concluded by the rules."""
        merged: dict[str, dict[str, float]] = {}
        for stage in self.result.stages:
            merged.update(stage.conclusions)
        return merged

    @property
    def warnings(self) -> tuple[str, ...]:
        return self.result.warnings


@dataclass(frozen=True, slots=True)
class CommandRanking:
    position: Position | None
    """The position whose players were compared (``None`` = every player)."""
    entries: tuple[CommandEvaluation, ...]
    """Best level first."""
    skipped: tuple[SkippedPlayer, ...]
    candidates: int
