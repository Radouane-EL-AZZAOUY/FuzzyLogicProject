"""Use case: rank every eligible candidate for a position."""

from __future__ import annotations

from dataclasses import dataclass, field

from fuzzyengine import EvaluationError
from fuzzyscout.domain.errors import MissingAttributesError
from fuzzyscout.domain.evaluation import (
    PlayerEvaluation,
    RankingEntry,
    RankingReport,
    SkippedPlayer,
)
from fuzzyscout.domain.evaluator import evaluate_player
from fuzzyscout.domain.filters import RankingFilters
from fuzzyscout.domain.ports import PipelineProvider, PlayerRepository, PositionCatalog


@dataclass(frozen=True, slots=True)
class RankingRequest:
    position_code: str
    filters: RankingFilters = field(default_factory=RankingFilters)
    limit: int | None = None
    """Keep only the ``limit`` best entries (``None`` = all)."""

    def __post_init__(self) -> None:
        if self.limit is not None and self.limit < 1:
            raise ValueError("La limite du classement doit être >= 1.")


@dataclass(frozen=True, slots=True)
class RankPlayers:
    players: PlayerRepository
    positions: PositionCatalog
    pipelines: PipelineProvider

    def execute(self, request: RankingRequest) -> RankingReport:
        position = self.positions.get(request.position_code)
        pipeline = self.pipelines.pipeline_for(position)
        candidates = self.players.all()
        evaluations: list[PlayerEvaluation] = []
        skipped: list[SkippedPlayer] = []
        for player in candidates:
            reason = request.filters.rejection_reason(player, position)
            if reason is not None:
                skipped.append(SkippedPlayer(player, reason))
                continue
            try:
                evaluations.append(evaluate_player(player, position, pipeline))
            except MissingAttributesError as exc:
                skipped.append(
                    SkippedPlayer(player, f"statistiques manquantes : {', '.join(exc.missing)}")
                )
            except EvaluationError as exc:
                # One bad candidate must never abort the whole report.
                skipped.append(SkippedPlayer(player, f"évaluation impossible : {exc}"))
        evaluations.sort(key=lambda e: (-e.aptitude, e.player.name))
        if request.limit is not None:
            evaluations = evaluations[: request.limit]
        entries = tuple(RankingEntry(rank, e) for rank, e in enumerate(evaluations, start=1))
        return RankingReport(
            position=position,
            filters=request.filters,
            entries=entries,
            skipped=tuple(skipped),
            candidates=len(candidates),
        )
