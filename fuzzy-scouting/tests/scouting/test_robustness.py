"""Boundary cases surfaced by code review: non-finite CSV cells, legacy encodings,
unreadable paths, blank or NaN API input, case-insensitive natural position."""

from __future__ import annotations

from pathlib import Path

import pytest

from fuzzyscout.application.scouting_service import ScoutingService
from fuzzyscout.domain.errors import DataSourceError
from fuzzyscout.domain.filters import RankingFilters
from fuzzyscout.domain.player import Player
from fuzzyscout.domain.position import Position
from fuzzyscout.infrastructure.csv_player_repository import CsvPlayerRepository
from fuzzyscout.interfaces.cli import main

from .conftest import STRIKER_STATS


@pytest.mark.parametrize("cell", ["nan", "NaN", "inf", "-inf", "1e999"])
def test_non_finite_csv_cells_are_rejected_with_location(tmp_path: Path, cell: str) -> None:
    path = tmp_path / "joueurs.csv"
    path.write_text(f"id,nom,age\nP1,Alpha,{cell}\n", encoding="utf-8")
    with pytest.raises(DataSourceError, match="Ligne 2, colonne 'age' : valeur non finie"):
        CsvPlayerRepository(path).all()


def test_windows_1252_csv_is_read_as_a_fallback(tmp_path: Path) -> None:
    path = tmp_path / "joueurs.csv"
    path.write_bytes("id;nom;age\nP1;Benzéma;25\n".encode("cp1252"))
    players = CsvPlayerRepository(path).all()
    assert players[0].name == "Benzéma" and players[0].age == 25


def test_directory_instead_of_file_is_a_data_source_error(tmp_path: Path) -> None:
    with pytest.raises(DataSourceError, match=r"Impossible de lire|introuvable"):
        CsvPlayerRepository(tmp_path).all()


def test_player_rejects_non_finite_and_non_numeric_attributes() -> None:
    with pytest.raises(ValueError, match="non fini"):
        Player("P1", "Nom", attributes={"age": float("nan")})
    with pytest.raises(ValueError, match="non numérique"):
        Player("P1", "Nom", attributes={"age": "vingt"})  # type: ignore[dict-item]


def test_natural_position_filter_is_case_insensitive() -> None:
    position = Position("attaquant", "Attaquant", ("a.toml",))
    player = Player("P1", "Nom", position="Attaquant")
    assert RankingFilters(natural_position_only=True).rejection_reason(player, position) is None


def test_cli_rejects_duplicate_ad_hoc_attributes(
    capsys: pytest.CaptureFixture[str], memory_service: ScoutingService
) -> None:
    code = main(
        ["evaluate", "--position", "attaquant", "--attr", "age=20", "--attr", "age=21"],
        service=memory_service,
    )
    assert code == 1 and "plusieurs fois" in capsys.readouterr().err


def test_cli_positions_and_validate_support_json(
    capsys: pytest.CaptureFixture[str], memory_service: ScoutingService
) -> None:
    assert main(["positions", "--json"], service=memory_service) == 0
    assert capsys.readouterr().out.lstrip().startswith("[")
    assert main(["validate", "--json"], service=memory_service) == 0
    assert '"nb_regles"' in capsys.readouterr().out


def test_api_rejects_blank_name_and_nan_with_422(memory_service: ScoutingService) -> None:
    fastapi = pytest.importorskip("fastapi")
    from fastapi.testclient import TestClient

    from fuzzyscout.interfaces.api.app import create_app

    assert fastapi is not None
    client = TestClient(create_app(service=memory_service))
    blank = client.post(
        "/evaluations/ad-hoc",
        json={"position": "attaquant", "attributes": STRIKER_STATS, "name": "   "},
    )
    assert blank.status_code == 422
    nan = client.post(
        "/evaluations/ad-hoc",
        content='{"position": "attaquant", "attributes": {"age": NaN}}',
        headers={"content-type": "application/json"},
    )
    assert nan.status_code == 422
    nan_filter = client.post(
        "/rankings",
        content='{"position": "attaquant", "max_age": NaN}',
        headers={"content-type": "application/json"},
    )
    assert nan_filter.status_code == 422
