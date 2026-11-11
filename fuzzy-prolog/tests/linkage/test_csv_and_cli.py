from __future__ import annotations

import json
from pathlib import Path

import pytest

from identitylink.infrastructure.csv_repository import (
    CsvRecordRepository,
    DataError,
    read_records,
    read_truth,
)
from identitylink.infrastructure.synthetic import generate_dataset
from identitylink.interfaces.cli import main


def test_csv_reader_accepts_bom_semicolons_cp1252_and_date_formats(tmp_path: Path) -> None:
    with_bom = tmp_path / "bom.csv"
    with_bom.write_text(
        "\ufeffid;nom;prenom;date_naissance;ville\np2;Tazi;Sara;1990;\n", encoding="utf-8"
    )
    records = CsvRecordRepository(with_bom).all()
    assert records[0].identifier == "p2" and str(records[0].birth) == "1990"
    legacy = tmp_path / "cp1252.csv"
    legacy.write_bytes(
        "id,nom,prenom,date_naissance\np1,Benzéma,Karim,19/12/1987\n".encode("cp1252")
    )
    record = read_records(legacy)[0]
    assert record.last_name == "Benzéma" and str(record.birth) == "1987-12-19"


@pytest.mark.parametrize(
    ("content", "fragment"),
    [
        ("id,nom\np1,a\n", "obligatoire"),
        ("id,nom,prenom\n,a,b\n", "identifiant vide"),
        ("id,nom,prenom\np1,a,b\np1,c,d\n", "dupliqué"),
        ("id,nom,prenom,date_naissance\np1,a,b,hier\n", "date invalide"),
        ("", "vide"),
    ],
)
def test_csv_reader_errors(tmp_path: Path, content: str, fragment: str) -> None:
    path = tmp_path / "bad.csv"
    path.write_text(content, encoding="utf-8")
    with pytest.raises(DataError, match=fragment):
        read_records(path)
    with pytest.raises(DataError, match="introuvable"):
        read_records(tmp_path / "absent.csv")


def test_truth_reader(tmp_path: Path) -> None:
    path = tmp_path / "verite.csv"
    path.write_text("id,personne\np1,X\np2,X\n", encoding="utf-8")
    assert read_truth(path) == {"p1": "X", "p2": "X"}
    path.write_text("id,qui\np1,X\n", encoding="utf-8")
    with pytest.raises(DataError, match="personne"):
        read_truth(path)


def test_generate_is_reproducible(tmp_path: Path) -> None:
    a = generate_dataset(tmp_path / "a", persons=20, seed=3)
    b = generate_dataset(tmp_path / "b", persons=20, seed=3)
    assert a[2] == b[2] >= 20
    assert (tmp_path / "a" / "personnes_exemple.csv").read_text(encoding="utf-8") == (
        tmp_path / "b" / "personnes_exemple.csv"
    ).read_text(encoding="utf-8")
    truth = read_truth(a[1])
    assert len(set(truth.values())) >= 20


def test_cli_dedupe_evaluate_query_generate(
    capsys: pytest.CaptureFixture[str], tmp_path: Path
) -> None:
    records, truth, count = generate_dataset(tmp_path, persons=25, seed=11)
    assert main(["dedupe", str(records), "--threshold", "0.7"]) == 0
    out = capsys.readouterr().out
    assert "Rapprochement d'identités" in out and f"{count} fiches" in out

    assert main(["dedupe", str(records), "--json", "--explain", "--all"]) == 0
    data = json.loads(capsys.readouterr().out)
    assert data["fiches"] == count and isinstance(data["paires"], list)
    if data["paires"]:
        assert "preuve" in data["paires"][0]

    assert (
        main(
            ["evaluate", str(records), "--truth", str(truth), "--thresholds", "0.6,0.8", "--errors"]
        )
        == 0
    )
    out = capsys.readouterr().out
    assert "précision" in out and "Faux positifs" in out

    assert main(["evaluate", str(records), "--truth", str(truth), "--json"]) == 0
    metrics = json.loads(capsys.readouterr().out)
    assert [m["seuil"] for m in metrics] == [0.5, 0.6, 0.7, 0.8, 0.9, 1.0]

    assert main(["query", str(records), "fiche(p0001, N, P, _, _, _).", "--explain"]) == 0
    assert "N = " in capsys.readouterr().out

    assert (
        main(
            [
                "--lambda-cut",
                "0.9",
                "--tnorm",
                "product",
                "query",
                str(records),
                "meme_personne(A, B).",
                "--max",
                "3",
            ]
        )
        == 0
    )
    capsys.readouterr()

    out_dir = tmp_path / "gen"
    assert main(["generate", "--out", str(out_dir), "--persons", "10", "--seed", "1"]) == 0
    assert (out_dir / "personnes_exemple.csv").exists()


def test_cli_errors(capsys: pytest.CaptureFixture[str], tmp_path: Path) -> None:
    assert main(["dedupe", str(tmp_path / "absent.csv")]) == 1
    assert "introuvable" in capsys.readouterr().err
    assert main(["dedupe", "--threshold", "2"]) == 1
    assert main(["query", "meme_personne(x"]) == 1
    assert "Erreur" in capsys.readouterr().err
