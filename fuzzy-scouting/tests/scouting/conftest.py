from __future__ import annotations

import pytest

from fuzzyscout.application.scouting_service import ScoutingService
from fuzzyscout.bootstrap import build_service
from fuzzyscout.config import Settings
from fuzzyscout.domain.player import Player
from fuzzyscout.infrastructure.memory import InMemoryPlayerRepository
from fuzzyscout.infrastructure.resources import default_knowledge_dir, default_players_csv
from fuzzyscout.infrastructure.toml_pipeline_provider import TomlPipelineProvider
from fuzzyscout.infrastructure.toml_position_catalog import TomlPositionCatalog

STRIKER_STATS = {
    "buts_p90": 0.75,
    "xg_p90": 0.62,
    "tirs_cadres_pct": 56,
    "passes_cles_p90": 1.6,
    "vitesse_max_kmh": 34.8,
    "distance_km_p90": 10.6,
    "duels_aeriens_pct": 55,
    "taille_cm": 185,
    "age": 24,
    "minutes_jouees": 2700,
    "blessures_jours": 8,
    "valeur_marche_meur": 12.0,
}

WEAK_STRIKER_STATS = {
    **STRIKER_STATS,
    "buts_p90": 0.12,
    "xg_p90": 0.15,
    "tirs_cadres_pct": 30,
    "passes_cles_p90": 0.6,
    "vitesse_max_kmh": 31.0,
    "distance_km_p90": 9.8,
    "age": 33,
    "minutes_jouees": 900,
    "blessures_jours": 95,
    "valeur_marche_meur": 1.5,
}


@pytest.fixture(scope="session")
def pipelines() -> TomlPipelineProvider:
    return TomlPipelineProvider(default_knowledge_dir())


@pytest.fixture(scope="session")
def positions() -> TomlPositionCatalog:
    return TomlPositionCatalog(default_knowledge_dir() / "positions.toml")


@pytest.fixture
def strong_striker() -> Player:
    return Player(
        "S1",
        "Buteur Fort",
        club="FC Test",
        nationality="MA",
        position="attaquant",
        attributes=STRIKER_STATS,
    )


@pytest.fixture
def weak_striker() -> Player:
    return Player(
        "S2",
        "Buteur Faible",
        club="FC Test",
        nationality="FR",
        position="attaquant",
        attributes=WEAK_STRIKER_STATS,
    )


@pytest.fixture
def incomplete_player() -> Player:
    return Player("S3", "Sans Stats", position="attaquant", attributes={"age": 20})


@pytest.fixture
def memory_service(
    strong_striker: Player,
    weak_striker: Player,
    incomplete_player: Player,
    positions: TomlPositionCatalog,
    pipelines: TomlPipelineProvider,
) -> ScoutingService:
    repository = InMemoryPlayerRepository([strong_striker, weak_striker, incomplete_player])
    return ScoutingService(repository, positions, pipelines)


@pytest.fixture(scope="session")
def sample_service() -> ScoutingService:
    return build_service(Settings(default_knowledge_dir(), default_players_csv()))
