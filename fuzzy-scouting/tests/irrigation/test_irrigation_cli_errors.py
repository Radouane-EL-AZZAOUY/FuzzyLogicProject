from __future__ import annotations

from pathlib import Path

import pytest

from fuzzyirrigation.cli import main


def test_batch_with_missing_column_is_a_clean_error(
    capsys: pytest.CaptureFixture[str], tmp_path: Path
) -> None:
    csv_path = tmp_path / "mesures.csv"
    csv_path.write_text("parcelle,humidite_sol,temperature\nA,12,35\n", encoding="utf-8")
    assert main(["batch", str(csv_path)]) == 1
    err = capsys.readouterr().err
    assert "colonne(s) manquante(s)" in err and "humidite_air" in err


def test_batch_with_bad_value_reports_the_line(
    capsys: pytest.CaptureFixture[str], tmp_path: Path
) -> None:
    csv_path = tmp_path / "mesures.csv"
    csv_path.write_text(
        "parcelle,humidite_sol,temperature,humidite_air\nA,12,35,20\nB,abc,22,60\n",
        encoding="utf-8",
    )
    assert main(["batch", str(csv_path)]) == 1
    assert "ligne 3" in capsys.readouterr().err
