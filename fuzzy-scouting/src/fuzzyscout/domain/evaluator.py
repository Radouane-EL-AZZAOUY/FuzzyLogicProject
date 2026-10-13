"""Domain service: evaluate one player for one position."""

from __future__ import annotations

from fuzzyengine import FuzzyPipeline
from fuzzyscout.domain.errors import MissingAttributesError
from fuzzyscout.domain.evaluation import PlayerEvaluation
from fuzzyscout.domain.player import Player
from fuzzyscout.domain.position import Position


def evaluate_player(
    player: Player, position: Position, pipeline: FuzzyPipeline
) -> PlayerEvaluation:
    """Run the position's pipeline on the player's attributes.

    Raises :class:`MissingAttributesError` when the player lacks a statistic the
    pipeline needs; callers decide whether that is fatal (single evaluation) or a
    reason to skip the player (ranking).
    """
    missing = player.missing(pipeline.required_inputs)
    if missing:
        raise MissingAttributesError(player.identifier, missing)
    values = {name: player.attributes[name] for name in pipeline.required_inputs}
    result = pipeline.evaluate(values)
    return PlayerEvaluation(
        player=player,
        position=position,
        result=result,
        final_output=pipeline.final_outputs[0],
    )
