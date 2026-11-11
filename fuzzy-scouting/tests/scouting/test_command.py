"""The « commande Scout » system: three deduced variables, then a level from 1 to 6."""

from __future__ import annotations

import itertools
import json
from pathlib import Path

import pytest

from fuzzyengine import Category, Degrees, Interval, Observation
from fuzzyscout.application.scout_command import ScoutCommand
from fuzzyscout.application.scouting_service import ScoutingService
from fuzzyscout.domain.errors import (
    DataSourceError,
    MissingAttributesError,
    PositionNotFoundError,
)
from fuzzyscout.infrastructure.csv_observation_repository import (
    CsvObservationRepository,
    read_observations_csv,
)
from fuzzyscout.infrastructure.toml_pipeline_provider import TomlPipelineProvider
from fuzzyscout.interfaces.cli import main

BEST: dict[str, Observation] = {
    "vitesse_max_kmh": 36.0,
    "temps_30m_s": 3.9,
    "sprints_p90": 30.0,
    "vitesse_changement_ms2": 6.0,
    "distance_deplacement_m": 12.0,
    "temps_reaction_s": 0.18,
    "tacles_p90": 4.0,
    "tacles_reussis_pct": 85.0,
    "fautes_p90": 0.5,
}
WORST: dict[str, Observation] = {
    "vitesse_max_kmh": 28.0,
    "temps_30m_s": 5.0,
    "sprints_p90": 5.0,
    "vitesse_changement_ms2": 2.0,
    "distance_deplacement_m": 6.0,
    "temps_reaction_s": 0.5,
    "tacles_p90": 0.5,
    "tacles_reussis_pct": 30.0,
    "fautes_p90": 3.0,
}
POINTS = {"faible": 0, "moyenne": 1, "fort": 2}
LEVEL_OF_TOTAL = {0: 1, 1: 2, 2: 2, 3: 3, 4: 4, 5: 5, 6: 6}


@pytest.fixture(scope="module")
def command(sample_service: ScoutingService) -> ScoutCommand:
    assert sample_service.command is not None
    return sample_service.command


def test_system_is_three_deductions_then_a_decision(pipelines: TomlPipelineProvider) -> None:
    pipeline = pipelines.command_pipeline()
    assert pipeline.chaining == "fuzzy"
    assert [stage.output_names for stage in pipeline.stages] == [
        ("vitesse",),
        ("acceleration",),
        ("tacle",),
        ("niveau",),
    ]
    assert pipeline.stages[1].input_names == (
        "vitesse_changement_ms2",
        "distance_deplacement_m",
        "temps_reaction_s",
    )
    assert pipeline.stages[3].input_names == ("vitesse", "acceleration", "tacle")
    assert all(len(stage.rule_base) == 27 for stage in pipeline.stages)
    assert len(pipeline.required_inputs) == 9
    for name in ("vitesse", "acceleration", "tacle"):
        assert pipeline.stages[3].inputs[name].labels == ("faible", "moyenne", "fort")
    assert len(pipeline.stages[3].outputs["niveau"].terms) == 6


@pytest.mark.parametrize("terms", list(itertools.product(("faible", "moyenne", "fort"), repeat=3)))
def test_decision_table_covers_the_27_combinations(
    pipelines: TomlPipelineProvider, terms: tuple[str, str, str]
) -> None:
    decision = pipelines.command_pipeline().stages[3]
    result = decision.evaluate(
        dict(zip(("vitesse", "acceleration", "tacle"), map(Category, terms), strict=True))
    )
    expected = LEVEL_OF_TOTAL[sum(POINTS[term] for term in terms)]
    assert result.outputs["niveau"] == pytest.approx(expected, abs=1e-3)
    assert result.label("niveau") == f"niveau_{expected}"
    assert len(result.fired_rules()) == 1
    assert (expected == 6) == (terms == ("fort", "fort", "fort"))


def test_extreme_players_reach_levels_six_and_one(command: ScoutCommand) -> None:
    best = command.evaluate_observations(BEST)
    assert best.level == 6 and best.labels["vitesse"] == "fort"
    assert best.conclusions["niveau"]["niveau_6"] == pytest.approx(1.0)
    worst = command.evaluate_observations(WORST)
    assert worst.level == 1 and set(worst.labels.values()) == {"faible", "niveau_1"}


def test_observations_may_be_values_intervals_or_categories(command: ScoutCommand) -> None:
    mixed = {
        **BEST,
        "temps_30m_s": Interval(4.0, 4.3),
        "sprints_p90": Category("moyen"),
        "temps_reaction_s": Category("court"),
    }
    evaluation = command.evaluate_observations(mixed, name="Mixte")
    speed = evaluation.result.stage("commande_vitesse")
    assert speed.fuzzified_inputs["temps_30m_s"] == pytest.approx(
        {"court": 1.0, "moyen": 1.0, "long": 0.0}
    )
    assert speed.fuzzified_inputs["sprints_p90"] == {"faible": 0.0, "moyen": 1.0, "eleve": 0.0}
    assert evaluation.level == 6 and evaluation.player.name == "Mixte"
    # The decision stage receives fuzzy conclusions, not defuzzified numbers.
    handed = evaluation.result.stage("commande_niveau").observations
    assert all(isinstance(value, Degrees) for value in handed.values())


def test_a_less_favourable_measure_never_raises_the_level(command: ScoutCommand) -> None:
    base = {**BEST, "vitesse_changement_ms2": 4.0, "distance_deplacement_m": 9.5}
    values = [
        round(command.evaluate_observations({**base, "temps_reaction_s": r}).level_value, 3)
        for r in (0.18, 0.24, 0.29, 0.33, 0.45)
    ]
    assert values == sorted(values, reverse=True) and values[0] > values[-1]


def test_missing_observation_is_reported(command: ScoutCommand) -> None:
    incomplete = {k: v for k, v in BEST.items() if k != "fautes_p90"}
    with pytest.raises(MissingAttributesError, match="fautes_p90"):
        command.evaluate_observations(incomplete)


def test_ranking_compares_players_of_the_same_position(command: ScoutCommand) -> None:
    report = command.rank("attaquant")
    assert report.position is not None and report.position.code == "attaquant"
    assert report.candidates == 9 and len(report.entries) == 9 and not report.skipped
    assert {entry.player.position for entry in report.entries} == {"attaquant"}
    values = [entry.level_value for entry in report.entries]
    assert values == sorted(values, reverse=True)
    assert command.rank("attaquant", limit=3).entries == report.entries[:3]
    with pytest.raises(PositionNotFoundError):
        command.rank("libero")


def test_packaged_dataset_is_fully_evaluated_and_partly_imprecise(command: ScoutCommand) -> None:
    report = command.rank()
    assert report.candidates == 40 and len(report.entries) == 40
    assert {entry.level for entry in report.entries} == {1, 2, 3, 4, 5, 6}
    kinds = {type(value) for entry in report.entries for value in entry.observations.values()}
    assert kinds == {float, Interval, Category}
    same = command.evaluate_player(report.entries[0].player.identifier)
    assert same.level_value == pytest.approx(report.entries[0].level_value)


def test_observation_csv_parsing(tmp_path: Path) -> None:
    path = tmp_path / "obs.csv"
    path.write_text(
        "id;nom;temps_30m_s;sprints_p90;fautes_p90\n"
        "P1;A;4,0..4,3;eleve;1,2\n"
        'P2;B;"[4,1 ; 4,4]";;\n',
        encoding="utf-8",
    )
    table = read_observations_csv(path)
    assert table["P1"] == {
        "temps_30m_s": Interval(4.0, 4.3),
        "sprints_p90": Category("eleve"),
        "fautes_p90": 1.2,
    }
    assert table["P2"] == {"temps_30m_s": Interval(4.1, 4.4)}
    assert CsvObservationRepository(path).for_player("absent") == {}


@pytest.mark.parametrize(
    ("content", "fragment"),
    [
        ("nom,x\nA,1\n", "colonne obligatoire absente"),
        ("id,x\nP1,1\nP1,2\n", "identifiant dupliqué"),
        ("id,x\nP1,5..4\n", "ligne 2, colonne 'x'"),
        ("id,x\nP1,nan\n", "non finie"),
    ],
)
def test_observation_csv_errors(tmp_path: Path, content: str, fragment: str) -> None:
    path = tmp_path / "obs.csv"
    path.write_text(content, encoding="utf-8")
    with pytest.raises(DataSourceError, match=fragment):
        read_observations_csv(path)


def test_cli_level_command(
    capsys: pytest.CaptureFixture[str], sample_service: ScoutingService
) -> None:
    assert main(["level", "--position", "attaquant", "--top", "2"], service=sample_service) == 0
    out = capsys.readouterr().out
    assert "Commande Scout" in out and "Candidats : 9 | classés : 2" in out

    observations = [f"--obs={name}={value}" for name, value in BEST.items()]
    observations[1] = "--obs=temps_30m_s=3.8..4.0"
    observations[2] = "--obs=sprints_p90=eleve"
    assert main(["level", *observations, "--explain"], service=sample_service) == 0
    out = capsys.readouterr().out
    assert "Niveau : 6 / 6" in out and "temps_30m_s = [3.8 ; 4]" in out
    assert "sprints_p90 = eleve" in out and "conclusion de l'étape précédente" in out

    assert main(["level", "--player", "P036", "--json"], service=sample_service) == 0
    data = json.loads(capsys.readouterr().out)
    assert 1 <= data["niveau"] <= 6 and set(data["variables"]) == {
        "vitesse",
        "acceleration",
        "tacle",
    }

    assert main(["level", "--obs", "sprints_p90=eleve"], service=sample_service) == 1
    assert "manquant" in capsys.readouterr().err


def test_api_command_endpoints(sample_service: ScoutingService) -> None:
    pytest.importorskip("fastapi")
    from fastapi.testclient import TestClient

    from fuzzyscout.interfaces.api.app import create_app

    client = TestClient(create_app(service=sample_service))
    system = client.get("/commande").json()
    assert system["niveaux"] == 6 and system["chainage"] == "fuzzy"
    assert system["variables_deduites"] == ["vitesse", "acceleration", "tacle"]
    assert [len(stage["regles"]) for stage in system["etapes"]] == [27, 27, 27, 27]
    assert {v["nom"] for v in system["variables"]} >= {"temps_reaction_s", "niveau"}

    body = {
        "observations": {
            **BEST,
            "temps_30m_s": "3.8..4.0",
            "vitesse_changement_ms2": [5.6, 6.4],
            "tacles_reussis_pct": {"min": 82, "max": 90},
            "fautes_p90": "faible",
        }
    }
    response = client.post("/commande/evaluations", json=body)
    assert response.status_code == 200, response.text
    data = response.json()
    assert data["niveau"] == 6 and data["variables"]["tacle"]["label"] == "fort"
    assert data["observations"]["temps_30m_s"]["type"] == "intervalle"
    assert data["observations"]["fautes_p90"] == {
        "type": "categorie",
        "texte": "faible",
        "terme": "faible",
        "valeur": None,
        "min": None,
        "max": None,
        "degres": None,
    }
    assert data["etapes"][3]["observations"]["vitesse"]["type"] == "degres"

    unknown = client.post(
        "/commande/evaluations", json={"observations": {**BEST, "fautes_p90": "rare"}}
    )
    assert unknown.status_code == 422 and "Catégorie inconnue" in unknown.json()["detail"]
    missing = client.post("/commande/evaluations", json={"observations": {"fautes_p90": 1}})
    assert missing.status_code == 422

    player = client.get("/commande/joueurs/P036")
    assert player.status_code == 200 and player.json()["joueur"]["poste"] == "attaquant"
    assert client.get("/commande/joueurs/zz").status_code == 404

    ranking = client.post("/commande/classements", json={"position": "gardien"}).json()
    assert ranking["poste"]["code"] == "gardien" and ranking["classes"] == 6
    assert [entry["rang"] for entry in ranking["classement"]] == list(range(1, 7))
    everyone = client.post("/commande/classements", json={}).json()
    assert everyone["poste"] is None and everyone["candidats"] == 40
    assert client.post("/commande/classements", json={"position": "x"}).status_code == 404


def test_api_reports_a_missing_command_system(memory_service: ScoutingService) -> None:
    pytest.importorskip("fastapi")
    from fastapi.testclient import TestClient

    from fuzzyscout.interfaces.api.app import create_app

    client = TestClient(create_app(service=memory_service))
    assert client.get("/commande").status_code == 404
