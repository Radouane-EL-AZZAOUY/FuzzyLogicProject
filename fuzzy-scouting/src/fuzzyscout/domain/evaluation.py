"""Results of evaluations and rankings (read models of the domain)."""

from __future__ import annotations

from dataclasses import dataclass

from fuzzyengine import PipelineResult, RuleActivation
from fuzzyscout.domain.filters import RankingFilters
from fuzzyscout.domain.player import Player
from fuzzyscout.domain.position import Position


@dataclass(frozen=True, slots=True)
class PlayerEvaluation:
    player: Player
    position: Position
    result: PipelineResult
    final_output: str
    """Name of the pipeline output holding the overall aptitude (e.g. ``aptitude``)."""

    @property
    def scores(self) -> dict[str, float]:
        """Every intermediate and final crisp score (``technique``, ``aptitude``...)."""
        return dict(self.result.outputs)

    @property
    def labels(self) -> dict[str, str]:
        return dict(self.result.labels)

    @property
    def aptitude(self) -> float:
        return self.result.outputs[self.final_output]

    @property
    def aptitude_label(self) -> str:
        return self.result.labels[self.final_output]

    @property
    def warnings(self) -> tuple[str, ...]:
        return self.result.warnings

    def strongest_rules(self, limit: int = 3) -> dict[str, list[RuleActivation]]:
        """Per stage, the ``limit`` most active rules (the core of the explanation)."""
        return {stage.system_name: stage.fired_rules()[:limit] for stage in self.result.stages}


@dataclass(frozen=True, slots=True)
class SkippedPlayer:
    player: Player
    reason: str


@dataclass(frozen=True, slots=True)
class RankingEntry:
    rank: int
    evaluation: PlayerEvaluation


@dataclass(frozen=True, slots=True)
class RankingReport:
    position: Position
    filters: RankingFilters
    entries: tuple[RankingEntry, ...]
    skipped: tuple[SkippedPlayer, ...]
    candidates: int
    """Number of players considered before filtering."""

    @property
    def ranked(self) -> int:
        return len(self.entries)
