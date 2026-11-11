"""Imprecise inputs (interval, category, degrees) and fuzzy chaining between stages."""

from __future__ import annotations

import pytest

from fuzzyengine import (
    Category,
    DefinitionError,
    Degrees,
    EvaluationError,
    FuzzyPipeline,
    FuzzySet,
    FuzzySystem,
    FuzzySystemBuilder,
    Interval,
    LinguisticVariable,
    Universe,
    explain_result,
    membership_from_spec,
    parse_observation,
    parse_rule,
)


def variable(name: str, low: str = "faible", mid: str = "moyen", high: str = "eleve"):
    return LinguisticVariable(
        name,
        Universe(0, 10),
        (
            FuzzySet(low, membership_from_spec("ramp_down", [2, 4])),
            FuzzySet(mid, membership_from_spec("triangle", [3, 5, 7])),
            FuzzySet(high, membership_from_spec("ramp_up", [6, 8])),
        ),
    )


def system(name: str, source: str, target: str) -> FuzzySystem:
    builder = FuzzySystemBuilder(name).add_input(variable(source)).add_output(variable(target))
    for index, term in enumerate(("faible", "moyen", "eleve")):
        builder.add_rule(
            parse_rule(f"SI {source} EST {term} ALORS {target} EST {term}", f"{name}{index}")
        )
    return builder.build()


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        (4.2, 4.2),
        ("4,2", 4.2),
        ("4.0..4.3", Interval(4.0, 4.3)),
        ("[4,0 ; 4,3]", Interval(4.0, 4.3)),
        ([4, 4.3], Interval(4.0, 4.3)),
        ({"min": 4, "max": 4.3}, Interval(4.0, 4.3)),
        (" moyen ", Category("moyen")),
        ({"eleve": 0.7}, Degrees({"eleve": 0.7})),
    ],
)
def test_parse_observation_accepts_every_form(raw: object, expected: object) -> None:
    assert parse_observation(raw) == expected


@pytest.mark.parametrize("raw", ["", "nan", "inf", "5..4", "4..", "12abc", True, [1, 2, 3], None])
def test_parse_observation_rejects_unusable_input(raw: object) -> None:
    with pytest.raises(EvaluationError):
        parse_observation(raw)


def test_interval_degree_is_the_best_membership_inside_it() -> None:
    result = system("s", "x", "y").evaluate({"x": Interval(4.5, 6.5)})
    # The peak of « moyen » (5) lies inside the interval; « eleve » only reaches 0.25 at 6.5.
    assert result.fuzzified_inputs["x"] == pytest.approx(
        {"faible": 0.0, "moyen": 1.0, "eleve": 0.25}
    )
    assert result.observations["x"] == Interval(4.5, 6.5)
    assert "x" not in result.inputs
    assert "x = [4.5 ; 6.5]" in explain_result(result)


def test_precise_value_is_a_degenerate_interval() -> None:
    engine = system("s", "x", "y")
    precise = engine.evaluate({"x": 6.4})
    degenerate = engine.evaluate({"x": Interval(6.4, 6.4)})
    assert degenerate.fuzzified_inputs["x"] == pytest.approx(precise.fuzzified_inputs["x"])
    assert degenerate.outputs["y"] == pytest.approx(precise.outputs["y"])


def test_wider_interval_never_lowers_a_degree() -> None:
    engine = system("s", "x", "y")
    narrow = engine.evaluate({"x": Interval(5.5, 6.0)}).fuzzified_inputs["x"]
    wide = engine.evaluate({"x": Interval(4.0, 7.5)}).fuzzified_inputs["x"]
    assert all(wide[term] >= narrow[term] for term in narrow)


def test_interval_outside_the_universe_is_clamped_with_a_warning() -> None:
    result = system("s", "x", "y").evaluate({"x": Interval(9, 14)})
    assert result.observations["x"] == Interval(9, 10)
    assert any("hors de l'univers" in warning for warning in result.warnings)


def test_category_makes_its_term_fully_true() -> None:
    result = system("s", "x", "y").evaluate({"x": Category("eleve")})
    assert result.fuzzified_inputs["x"] == {"faible": 0.0, "moyen": 0.0, "eleve": 1.0}
    assert result.label("y") == "eleve"


def test_unknown_category_and_bad_degrees_are_rejected() -> None:
    engine = system("s", "x", "y")
    with pytest.raises(EvaluationError, match="Catégorie inconnue 'rapide'"):
        engine.evaluate({"x": Category("rapide")})
    with pytest.raises(EvaluationError, match="Terme"):
        engine.evaluate({"x": Degrees({"rapide": 0.5})})
    with pytest.raises(EvaluationError, match="hors de"):
        Degrees({"eleve": 1.5})
    with pytest.raises(EvaluationError, match="borne inférieure"):
        Interval(5, 4)


def test_conclusions_report_the_degree_of_each_output_term() -> None:
    result = system("s", "x", "y").evaluate({"x": 6.5})
    assert result.conclusions["y"] == pytest.approx({"faible": 0.0, "moyen": 0.25, "eleve": 0.25})


def test_fuzzy_chaining_hands_over_the_conclusion_itself() -> None:
    stages = (system("a", "x", "y"), system("b", "y", "z"))
    crisp = FuzzyPipeline("p", stages).evaluate({"x": 6.5})
    fuzzy = FuzzyPipeline("p", stages, chaining="fuzzy").evaluate({"x": 6.5})
    # Crisp chaining re-fuzzifies the defuzzified number; fuzzy chaining keeps both terms.
    handed = fuzzy.stage("b").observations["y"]
    assert isinstance(handed, Degrees)
    assert dict(handed.degrees) == pytest.approx({"faible": 0.0, "moyen": 0.25, "eleve": 0.25})
    assert fuzzy.stage("b").fuzzified_inputs["y"] == pytest.approx(
        fuzzy.stage("a").conclusions["y"]
    )
    assert isinstance(crisp.stage("b").observations["y"], float)
    assert crisp.stage("b").fuzzified_inputs["y"] != pytest.approx(
        fuzzy.stage("b").fuzzified_inputs["y"]
    )


def test_unknown_chaining_is_rejected() -> None:
    with pytest.raises(DefinitionError, match="chaînage inconnu"):
        FuzzyPipeline("p", (system("a", "x", "y"),), chaining="flou")
