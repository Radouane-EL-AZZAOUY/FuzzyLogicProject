"""Composition root: wires concrete adapters into the application service.

This is the only module allowed to know both the application layer and the
infrastructure layer (including where the packaged defaults live).
"""

from __future__ import annotations

import logging

from fuzzyscout.application.scouting_service import ScoutingService
from fuzzyscout.config import Settings
from fuzzyscout.infrastructure.csv_player_repository import CsvPlayerRepository
from fuzzyscout.infrastructure.resources import default_knowledge_dir, default_players_csv
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
    return ScoutingService(
        players=CsvPlayerRepository(players_csv),
        positions=TomlPositionCatalog(knowledge_dir / POSITIONS_FILE),
        pipelines=TomlPipelineProvider(knowledge_dir),
    )
