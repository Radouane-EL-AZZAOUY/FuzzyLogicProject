"""Use cases of the « commande Scout » system.

* case 1 — one player: :meth:`ScoutCommand.evaluate_observations` (free input) and
  :meth:`ScoutCommand.evaluate_player` (a player of the dataset);
* case 2 — a dataset of players of the same position: :meth:`ScoutCommand.rank`.
"""

from __future__ import annotations

from collections.abc import Callable, Mapping

from fuzzyengine import EvaluationError, FuzzyPipeline, Observation
from fuzzyscout.domain.command import CommandEvaluation, CommandRanking
from fuzzyscout.domain.errors import MissingAttributesError
from fuzzyscout.domain.evaluation import SkippedPlayer
from fuzzyscout.domain.player import Player
from fuzzyscout.domain.ports import ObservationRepository, PlayerRepository, PositionCatalog


class ScoutCommand:
    def __init__(
        self,
        players: PlayerRepository,
        positions: PositionCatalog,
        observations: ObservationRepository,
        pipeline_loader: Callable[[], FuzzyPipeline],
    ) -> None:
        self._players = players
        self._positions = positions
        self._observations = observations
        self._load_pipeline = pipeline_loader

    @property
    def pipeline(self) -> FuzzyPipeline:
        """The hierarchical system (loaded and validated on first use, then cached)."""
        return self._load_pipeline()

    def observations_of(self, player: Player) -> dict[str, Observation]:
        """Everything known about ``player``: measured statistics, then the (possibly
        imprecise) observations recorded for the system, which take precedence."""
        known: dict[str, Observation] = dict(player.attributes)
        known.update(self._observations.for_player(player.identifier))
        return known

    def _evaluate(self, player: Player, known: Mapping[str, Observation]) -> CommandEvaluation:
        pipeline = self.pipeline
        missing = tuple(name for name in pipeline.required_inputs if name not in known)
        if missing:
            raise MissingAttributesError(player.identifier, missing)
        used = {name: known[name] for name in pipeline.required_inputs}
        return CommandEvaluation(
            player=player,
            observations=used,
            result=pipeline.evaluate(used),
            final_output=pipeline.final_outputs[0],
        )

    def evaluate_observations(
        self, observations: Mapping[str, Observation], name: str = "Joueur observé"
    ) -> CommandEvaluation:
        """Case 1: a player described only by what was observed."""
        return self._evaluate(Player(identifier="adhoc", name=name), observations)

    def evaluate_player(self, player_identifier: str) -> CommandEvaluation:
        """Case 1: a player of the dataset."""
        player = self._players.get(player_identifier)
        return self._evaluate(player, self.observations_of(player))

    def rank(self, position_code: str | None = None, limit: int | None = None) -> CommandRanking:
        """Case 2: every player of ``position_code`` (or everyone), best level first."""
        if limit is not None and limit < 1:
            raise ValueError("La limite du classement doit être >= 1.")
        position = self._positions.get(position_code) if position_code else None
        candidates = [
            player
            for player in self._players.all()
            if position is None or player.position.casefold() == position.code.casefold()
        ]
        evaluations: list[CommandEvaluation] = []
        skipped: list[SkippedPlayer] = []
        for player in candidates:
            try:
                evaluations.append(self._evaluate(player, self.observations_of(player)))
            except MissingAttributesError as exc:
                skipped.append(
                    SkippedPlayer(player, f"observations manquantes : {', '.join(exc.missing)}")
                )
            except EvaluationError as exc:
                skipped.append(SkippedPlayer(player, f"évaluation impossible : {exc}"))
        evaluations.sort(key=lambda e: (-e.level_value, e.player.name))
        if limit is not None:
            evaluations = evaluations[:limit]
        return CommandRanking(position, tuple(evaluations), tuple(skipped), len(candidates))
