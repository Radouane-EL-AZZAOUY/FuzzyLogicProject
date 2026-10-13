from __future__ import annotations

import json
from pathlib import Path

import pytest

from fuzzyirrigation.advisor import IrrigationAdvisor
from fuzzyirrigation.cli import main
from fuzzyirrigation.domain import SensorReading


@pytest.fixture(scope="module")
def advisor() -> IrrigationAdvisor:
    return IrrigationAdvisor.from_file()


def test_dry_hot_plot_gets_a_long_watering(advisor: IrrigationAdvisor) -> None:
    decision = advisor.decide(
        SensorReading(humidite_sol=15, temperature=36, humidite_air=25, pluie_prevue_mm=0)
    )
    assert (
        decision.should_irrigate and decision.label == "longue" and decision.duration_minutes > 40
    )


def test_wet_plot_or_rain_forecast_means_no_watering(advisor: IrrigationAdvisor) -> None:
    wet = advisor.decide(
        SensorReading(humidite_sol=75, temperature=30, humidite_air=40, pluie_prevue_mm=0)
    )
    rain = advisor.decide(
        SensorReading(humidite_sol=15, temperature=36, humidite_air=25, pluie_prevue_mm=25)
    )
    assert not wet.should_irrigate and not rain.should_irrigate
    assert wet.label == "nulle" and rain.label == "nulle"


def test_duration_decreases_with_soil_moisture(advisor: IrrigationAdvisor) -> None:
    durations = [
        advisor.decide(SensorReading(h, 28, 45, 0)).duration_minutes
        for h in (10, 25, 40, 55, 70, 90)
    ]
    assert durations == sorted(durations, reverse=True)


def test_reading_validation() -> None:
    with pytest.raises(ValueError):
        SensorReading(120, 20, 40, 0)
    with pytest.raises(ValueError):
        SensorReading(20, 20, 40, -1)


def test_cli_decide_and_batch(capsys: pytest.CaptureFixture[str], tmp_path: Path) -> None:
    code = main(
        [
            "decide",
            "--humidite-sol",
            "15",
            "--temperature",
            "36",
            "--humidite-air",
            "25",
            "--explain",
        ]
    )
    out = capsys.readouterr().out
    assert code == 0 and "arroser" in out and "longue" in out and "[I9]" in out

    code = main(
        ["decide", "--humidite-sol", "80", "--temperature", "20", "--humidite-air", "60", "--json"]
    )
    data = json.loads(capsys.readouterr().out)
    assert code == 0 and data["arroser"] is False

    csv_path = tmp_path / "mesures.csv"
    csv_path.write_text(
        "parcelle,humidite_sol,temperature,humidite_air,pluie_prevue_mm\nA,12,35,20,0\nB,70,22,60,0\n",
        encoding="utf-8",
    )
    code = main(["batch", str(csv_path), "--json"])
    rows = json.loads(capsys.readouterr().out)
    assert (
        code == 0
        and [r["parcelle"] for r in rows] == ["A", "B"]
        and rows[0]["arroser"]
        and not rows[1]["arroser"]
    )

    assert (
        main(["decide", "--humidite-sol", "150", "--temperature", "20", "--humidite-air", "60"])
        == 1
    )
    assert "Erreur" in capsys.readouterr().err
