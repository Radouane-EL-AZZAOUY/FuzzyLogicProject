from pathlib import Path

import pytest

from fuzzyengine import (
    KnowledgeBaseError,
    MamdaniInference,
    load_library,
    load_pipeline,
    load_system,
    load_system_from_dict,
)

SYSTEM_TOML = """
[system]
name = "demo"
description = "démo"
operators = "probabilistic"
implication = "product"
aggregation = "probabilistic_sum"
defuzzifier = "centroid"
resolution = 201

[[inputs]]
name = "vitesse"
universe = [0, 100]
unit = "km/h"
[inputs.terms]
lente = { kind = "ramp_down", params = [20, 40] }
rapide = { kind = "ramp_up", params = [60, 80] }

[[outputs]]
name = "score"
universe = [0, 100]
[outputs.terms]
faible = { kind = "trapezoid", params = [0, 0, 25, 45] }
bon = { kind = "trapezoid", params = [55, 75, 100, 100] }

[[rules]]
id = "R1"
text = "SI vitesse EST rapide ALORS score EST bon"
description = "vitesse valorisée"

[[rules]]
text = "SI vitesse EST lente ALORS score EST faible"
weight = 0.5
"""

LIBRARY_TOML = """
[[variables]]
name = "score"
universe = [0, 100]
[variables.terms]
faible = { kind = "trapezoid", params = [0, 0, 25, 45] }
bon = { kind = "trapezoid", params = [55, 75, 100, 100] }
"""


def test_load_system_from_file_with_all_options(tmp_path: Path) -> None:
    path = tmp_path / "demo.toml"
    path.write_text(SYSTEM_TOML, encoding="utf-8")
    system = load_system(path)
    assert system.name == "demo" and system.description == "démo"
    assert system.input_names == ("vitesse",) and system.output_names == ("score",)
    assert system.inputs["vitesse"].unit == "km/h"
    inference = system.inference
    assert isinstance(inference, MamdaniInference)
    assert inference.operators.name == "probabilistic"
    assert inference.implication.name == "product"
    assert inference.aggregation.name == "probabilistic_sum"
    assert system.defuzzifier.resolution == 201  # type: ignore[attr-defined]
    rules = list(system.rule_base)
    assert [r.identifier for r in rules] == ["R1", "R2"]
    assert rules[0].description == "vitesse valorisée" and rules[1].weight == 0.5
    assert system.evaluate({"vitesse": 95}).label("score") == "bon"


def test_shared_library_references(tmp_path: Path) -> None:
    (tmp_path / "lib.toml").write_text(LIBRARY_TOML, encoding="utf-8")
    library = load_library(tmp_path / "lib.toml")
    assert set(library) == {"score"}
    text = SYSTEM_TOML.replace(
        '[[outputs]]\nname = "score"\nuniverse = [0, 100]\n[outputs.terms]\n'
        'faible = { kind = "trapezoid", params = [0, 0, 25, 45] }\n'
        'bon = { kind = "trapezoid", params = [55, 75, 100, 100] }',
        '[[outputs]]\nref = "score"',
    )
    assert 'ref = "score"' in text
    (tmp_path / "sys.toml").write_text(text, encoding="utf-8")
    system = load_system(tmp_path / "sys.toml", library)
    assert system.outputs["score"] is library["score"]
    with pytest.raises(KnowledgeBaseError, match="variable partagée inconnue"):
        load_system(tmp_path / "sys.toml")


def test_missing_file_and_invalid_toml(tmp_path: Path) -> None:
    with pytest.raises(KnowledgeBaseError, match="introuvable"):
        load_system(tmp_path / "nope.toml")
    bad = tmp_path / "bad.toml"
    bad.write_text("[system\nname = 1", encoding="utf-8")
    with pytest.raises(KnowledgeBaseError, match="TOML invalide"):
        load_system(bad)


def _base_dict() -> dict:  # type: ignore[type-arg]
    return {
        "system": {"name": "s"},
        "inputs": [
            {
                "name": "v",
                "universe": [0, 10],
                "terms": {"x": {"kind": "triangle", "params": [0, 5, 10]}},
            }
        ],
        "outputs": [
            {
                "name": "o",
                "universe": [0, 10],
                "terms": {"y": {"kind": "triangle", "params": [0, 5, 10]}},
            }
        ],
        "rules": [{"text": "SI v EST x ALORS o EST y"}],
    }


@pytest.mark.parametrize(
    ("mutate", "fragment"),
    [
        (lambda d: d.pop("system"), "clé obligatoire manquante : 'system'"),
        (lambda d: d["system"].pop("name"), "'name'"),
        (lambda d: d["system"].update(name=3), "type str"),
        (lambda d: d["inputs"][0].update(universe=[0]), "deux nombres"),
        (lambda d: d["inputs"][0].update(terms={}), "vide"),
        (lambda d: d["inputs"][0]["terms"].update(z="oops"), "table"),
        (lambda d: d["inputs"][0]["terms"]["x"].update(kind="hexagon"), "inconnue"),
        (lambda d: d["inputs"][0]["terms"]["x"].update(params=[1]), "paramètres"),
        (lambda d: d["rules"][0].update(text="SI v x ALORS o EST y"), "règle 'R1' invalide"),
        (lambda d: d["rules"][0].update(text="SI v EST z ALORS o EST y"), "terme inconnu 'z'"),
        (lambda d: d["rules"][0].update(weight=2), "poids"),
        (lambda d: d["system"].update(operators="boolean"), "Famille"),
        (lambda d: d["system"].update(defuzzifier="median"), "défuzzification"),
        (lambda d: d["inputs"].append(dict(d["inputs"][0])), "deux fois"),
        (lambda d: d.update(inputs="v"), "type list"),
    ],
)
def test_loader_diagnostics(mutate, fragment: str) -> None:  # type: ignore[no-untyped-def]
    data = _base_dict()
    mutate(data)
    with pytest.raises(KnowledgeBaseError, match=fragment):
        load_system_from_dict(data, "test")


def test_load_pipeline(tmp_path: Path) -> None:
    (tmp_path / "a.toml").write_text(SYSTEM_TOML, encoding="utf-8")
    second = SYSTEM_TOML.replace('name = "demo"', 'name = "demo2"').replace(
        'name = "score"', 'name = "score2"'
    )
    second = second.replace("ALORS score EST", "ALORS score2 EST")
    (tmp_path / "b.toml").write_text(second, encoding="utf-8")
    pipeline = load_pipeline("p", [tmp_path / "a.toml", tmp_path / "b.toml"])
    assert pipeline.produced_outputs == ("score", "score2")
    with pytest.raises(KnowledgeBaseError, match="deux fois"):
        load_pipeline("p", [tmp_path / "a.toml", tmp_path / "a.toml"])
    third = SYSTEM_TOML.replace('name = "demo"', 'name = "demo3"')
    (tmp_path / "c.toml").write_text(third, encoding="utf-8")
    with pytest.raises(KnowledgeBaseError, match="plusieurs étapes"):
        load_pipeline("p", [tmp_path / "a.toml", tmp_path / "c.toml"])
