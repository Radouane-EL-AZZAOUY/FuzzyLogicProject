from __future__ import annotations

import json

import pytest

from fuzzyscout.application.scouting_service import ScoutingService
from fuzzyscout.interfaces.cli import main


def run(
    capsys: pytest.CaptureFixture[str], service: ScoutingService, *argv: str
) -> tuple[int, str, str]:
    code = main(list(argv), service=service)
    captured = capsys.readouterr()
    return code, captured.out, captured.err


def test_positions_command(
    capsys: pytest.CaptureFixture[str], memory_service: ScoutingService
) -> None:
    code, out, _ = run(capsys, memory_service, "positions")
    assert code == 0 and "attaquant" in out and "Gardien de but" in out


def test_rank_text_and_json(
    capsys: pytest.CaptureFixture[str], memory_service: ScoutingService
) -> None:
    code, out, _ = run(
        capsys, memory_service, "rank", "--position", "attaquant", "--top", "1", "--explain"
    )
    assert code == 0
    assert "Classement" in out and "Buteur Fort" in out and "Exclus" in out and "force=" in out
    code, out, _ = run(
        capsys, memory_service, "rank", "--position", "attaquant", "--json", "--max-age", "30"
    )
    data = json.loads(out)
    assert code == 0 and data["classes"] == 1 and data["filtres"] == ["âge ≤ 30"]
    assert data["classement"][0]["joueur"]["id"] == "S1"


def test_evaluate_player_and_ad_hoc(
    capsys: pytest.CaptureFixture[str], memory_service: ScoutingService
) -> None:
    code, out, _ = run(
        capsys, memory_service, "evaluate", "--position", "attaquant", "--player", "S1", "--explain"
    )
    assert code == 0 and "Aptitude" in out and "Pourquoi" in out and "technique_attaquant" in out
    code, out, _ = run(
        capsys,
        memory_service,
        "evaluate",
        "--position",
        "attaquant",
        "--json",
        "--attr",
        "buts_p90=0.7",
        "--attr",
        "xg_p90=0,6",
        "--attr",
        "tirs_cadres_pct=50",
        "--attr",
        "passes_cles_p90=1.5",
        "--attr",
        "vitesse_max_kmh=34",
        "--attr",
        "distance_km_p90=10.5",
        "--attr",
        "duels_aeriens_pct=55",
        "--attr",
        "taille_cm=185",
        "--attr",
        "age=24",
        "--attr",
        "minutes_jouees=2500",
        "--attr",
        "blessures_jours=5",
        "--name",
        "Essai",
    )
    data = json.loads(out)
    assert code == 0 and data["joueur"]["nom"] == "Essai" and data["aptitude"] > 60
    assert "etapes" not in data


def test_validate_command(
    capsys: pytest.CaptureFixture[str], memory_service: ScoutingService
) -> None:
    code, out, _ = run(capsys, memory_service, "validate")
    assert code == 0 and "valides" in out and "aptitude_commune" in out


def test_errors_give_exit_code_1(
    capsys: pytest.CaptureFixture[str], memory_service: ScoutingService
) -> None:
    code, _, err = run(
        capsys, memory_service, "evaluate", "--position", "attaquant", "--player", "ghost"
    )
    assert code == 1 and "Joueur inconnu" in err
    code, _, err = run(
        capsys, memory_service, "evaluate", "--position", "attaquant", "--player", "S3"
    )
    assert code == 1 and "manquant" in err
    code, _, err = run(capsys, memory_service, "rank", "--position", "libero")
    assert code == 1 and "Poste inconnu" in err


def test_bad_attribute_syntax_is_a_usage_error(
    capsys: pytest.CaptureFixture[str], memory_service: ScoutingService
) -> None:
    with pytest.raises(SystemExit) as info:
        main(["evaluate", "--position", "attaquant", "--attr", "buts_p90"], service=memory_service)
    assert info.value.code == 2
