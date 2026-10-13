"""Facade exposing every use case to the interfaces (CLI, HTTP API)."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass

from fuzzyscout.application.evaluate_player import EvaluatePlayer
from fuzzyscout.application.rank_players import RankingRequest, RankPlayers
from fuzzyscout.domain.evaluation import PlayerEvaluation, RankingReport
from fuzzyscout.domain.player import Player
from fuzzyscout.domain.ports import PipelineProvider, PlayerRepository, PositionCatalog
from fuzzyscout.domain.position import Position


@dataclass(frozen=True, slots=True)
class StageSummary:
    name: str
    inputs: tuple[str, ...]
    outputs: tuple[str, ...]
    rules: int


@dataclass(frozen=True, slots=True)
class KnowledgeSummary:
    """What the knowledge bases of one position look like once loaded and validated."""

    position: Position
    required_inputs: tuple[str, ...]
    stages: tuple[StageSummary, ...]

    @property
    def rules(self) -> int:
        return sum(stage.rules for stage in self.stages)


class ScoutingService:
    def __init__(
        self,
        players: PlayerRepository,
        positions: PositionCatalog,
        pipelines: PipelineProvider,
    ) -> None:
        self._players = players
        self._positions = positions
        self._pipelines = pipelines
        self._evaluate = EvaluatePlayer(players, positions, pipelines)
        self._rank = RankPlayers(players, positions, pipelines)

    # --- queries ---------------------------------------------------------------

    def positions(self) -> Sequence[Position]:
        return self._positions.all()

    def players(self) -> Sequence[Player]:
        return self._players.all()

    def player(self, identifier: str) -> Player:
        return self._players.get(identifier)

    # --- use cases -------------------------------------------------------------

    def evaluate(self, position_code: str, player_identifier: str) -> PlayerEvaluation:
        return self._evaluate.by_identifier(position_code, player_identifier)

    def evaluate_attributes(
        self, position_code: str, attributes: Mapping[str, float], name: str = "Candidat ad hoc"
    ) -> PlayerEvaluation:
        return self._evaluate.from_attributes(position_code, attributes, name)

    def rank(self, request: RankingRequest) -> RankingReport:
        return self._rank.execute(request)

    def validate_knowledge(self) -> list[KnowledgeSummary]:
        """Load every position's pipeline; raises on the first invalid knowledge base."""
        summaries: list[KnowledgeSummary] = []
        for position in self._positions.all():
            pipeline = self._pipelines.pipeline_for(position)
            stages = tuple(
                StageSummary(s.name, s.input_names, s.output_names, len(s.rule_base))
                for s in pipeline.stages
            )
            summaries.append(KnowledgeSummary(position, pipeline.required_inputs, stages))
        return summaries
