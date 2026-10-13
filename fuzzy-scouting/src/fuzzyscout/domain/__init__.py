"""Domain layer: pure business objects, free of any I/O."""

from fuzzyscout.domain.errors import (
    DataSourceError,
    MissingAttributesError,
    PlayerNotFoundError,
    PositionNotFoundError,
    ScoutingError,
)
from fuzzyscout.domain.evaluation import (
    PlayerEvaluation,
    RankingEntry,
    RankingReport,
    SkippedPlayer,
)
from fuzzyscout.domain.evaluator import evaluate_player
from fuzzyscout.domain.filters import RankingFilters
from fuzzyscout.domain.player import Player
from fuzzyscout.domain.ports import PipelineProvider, PlayerRepository, PositionCatalog
from fuzzyscout.domain.position import Position

__all__ = [
    "DataSourceError",
    "MissingAttributesError",
    "PipelineProvider",
    "Player",
    "PlayerEvaluation",
    "PlayerNotFoundError",
    "PlayerRepository",
    "Position",
    "PositionCatalog",
    "PositionNotFoundError",
    "RankingEntry",
    "RankingFilters",
    "RankingReport",
    "ScoutingError",
    "SkippedPlayer",
    "evaluate_player",
]
