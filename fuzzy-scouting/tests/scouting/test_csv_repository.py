from pathlib import Path

import pytest

from fuzzyscout.domain.errors import DataSourceError, PlayerNotFoundError
from fuzzyscout.infrastructure.csv_player_repository import CsvPlayerRepository, parse_players


def test_parse_players_converts_numbers_and_skips_empty_cells() -> None:
    rows = [
        {
            "id": "P1",
            "nom": "A",
            "club": "C",
            "nationalite": "MA",
            "poste": "ailier",
            "age": "24",
            "buts_p90": "0,45",
            "arrets_pct": "",
        },
        {
            "id": "P2",
            "nom": "B",
            "club": "",
            "nationalite": "",
            "poste": "",
            "age": "30",
            "buts_p90": "",
            "arrets_pct": "71.5",
        },
    ]
    players = parse_players(rows)
    assert players[0].attributes == {"age": 24.0, "buts_p90": 0.45}
    assert players[0].club == "C" and players[0].position == "ailier"
    assert players[1].attributes == {"age": 30.0, "arrets_pct": 71.5}


@pytest.mark.parametrize(
    ("rows", "fragment"),
    [
        ([{"id": "", "nom": "A"}], "colonne obligatoire 'id'"),
        ([{"id": "P1", "nom": " "}], "colonne obligatoire 'nom'"),
        ([{"id": "P1", "nom": "A"}, {"id": "P1", "nom": "B"}], "dupliqué"),
        ([{"id": "P1", "nom": "A", "age": "vingt"}], "valeur numérique invalide"),
    ],
)
def test_parse_players_errors(rows, fragment: str) -> None:  # type: ignore[no-untyped-def]
    with pytest.raises(DataSourceError, match=fragment):
        parse_players(rows)


def test_repository_reads_semicolon_csv_with_bom(tmp_path: Path) -> None:
    path = tmp_path / "joueurs.csv"
    path.write_text(
        "﻿id;nom;club;age;buts_p90\nP1;Alpha;FC;25;0,5\nP2;Beta;FC;;\n", encoding="utf-8"
    )
    repository = CsvPlayerRepository(path)
    assert [p.identifier for p in repository.all()] == ["P1", "P2"]
    assert repository.get("P1").attributes == {"age": 25.0, "buts_p90": 0.5}
    assert repository.get("P2").attributes == {}
    with pytest.raises(PlayerNotFoundError):
        repository.get("P9")


def test_repository_file_errors(tmp_path: Path) -> None:
    with pytest.raises(DataSourceError, match="introuvable"):
        CsvPlayerRepository(tmp_path / "absent.csv").all()
    empty = tmp_path / "empty.csv"
    empty.write_text("", encoding="utf-8")
    with pytest.raises(DataSourceError, match="vide"):
        CsvPlayerRepository(empty).all()
    bad = tmp_path / "bad.csv"
    bad.write_text("identifiant,nom\n1,A\n", encoding="utf-8")
    with pytest.raises(DataSourceError, match="obligatoire"):
        CsvPlayerRepository(bad).all()
