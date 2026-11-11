"""Composition root: wires concrete adapters into the application service.

This is the only module allowed to know both the application layer and the
infrastructure layer (including where the packaged defaults live).
"""

from __future__ import annotations

import logging

from fuzzyscout.application.scout_command import ScoutCommand
from fuzzyscout.application.scouting_service import ScoutingService
from fuzzyscout.config import Settings
from fuzzyscout.domain.ports import ObservationRepository
from fuzzyscout.infrastructure.csv_observation_repository import (
    CsvObservationRepository,
    NoObservations,
)
from fuzzyscout.infrastructure.csv_player_repository import CsvPlayerRepository
from fuzzyscout.infrastructure.resources import (
    default_knowledge_dir,
    default_observations_csv,
    default_players_csv,
)
from fuzzyscout.infrastructure.toml_pipeline_provider import TomlPipelineProvider
from fuzzyscout.infrastructure.toml_position_catalog import TomlPositionCatalog

POSITIONS_FILE = "positions.toml"


def configure_logging(level: str) -> None:
    logging.basicConfig(
        level=getattr(logging, level.upper(), logging.INFO),
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )


def build_service(settings: Settings | None = None) -> ScoutingService:
    settings = settings or Settings.from_env()
    knowledge_dir = settings.knowledge_dir or default_knowledge_dir()
    players_csv = settings.players_csv or default_players_csv()
    logging.getLogger(__name__).debug("knowledge_dir=%s players_csv=%s", knowledge_dir, players_csv)
    players = CsvPlayerRepository(players_csv)
    positions = TomlPositionCatalog(knowledge_dir / POSITIONS_FILE)
    pipelines = TomlPipelineProvider(knowledge_dir)
    command = None
    if pipelines.has_command:
        command = ScoutCommand(
            players, positions, _observations(settings), pipelines.command_pipeline
        )
    return ScoutingService(players, positions, pipelines, command)


def _observations(settings: Settings) -> ObservationRepository:
    if settings.observations_csv is not None:
        return CsvObservationRepository(settings.observations_csv)
    if settings.players_csv is None or settings.players_csv == default_players_csv():
        # The packaged observations describe the packaged players only.
        return CsvObservationRepository(default_observations_csv())
    return NoObservations()
