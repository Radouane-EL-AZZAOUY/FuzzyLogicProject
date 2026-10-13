"""Use case: evaluate a single candidate for a position."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass

from fuzzyscout.domain.evaluation import PlayerEvaluation
from fuzzyscout.domain.evaluator import evaluate_player
from fuzzyscout.domain.player import Player
from fuzzyscout.domain.ports import PipelineProvider, PlayerRepository, PositionCatalog


@dataclass(frozen=True, slots=True)
class EvaluatePlayer:
    players: PlayerRepository
    positions: PositionCatalog
    pipelines: PipelineProvider

    def by_identifier(self, position_code: str, player_identifier: str) -> PlayerEvaluation:
        """Evaluate a player stored in the repository."""
        position = self.positions.get(position_code)
        player = self.players.get(player_identifier)
        return evaluate_player(player, position, self.pipelines.pipeline_for(position))

    def from_attributes(
        self,
        position_code: str,
        attributes: Mapping[str, float],
        name: str = "Candidat ad hoc",
        identifier: str = "adhoc",
    ) -> PlayerEvaluation:
        """Evaluate a transient player described only by its attributes (what-if analysis)."""
        position = self.positions.get(position_code)
        player = Player(identifier=identifier, name=name, attributes=dict(attributes))
        return evaluate_player(player, position, self.pipelines.pipeline_for(position))
