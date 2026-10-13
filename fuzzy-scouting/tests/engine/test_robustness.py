"""Boundary cases surfaced by code review: non-finite inputs, grid-invisible outputs,
mis-ordered pipelines, non-numeric parameters."""

from __future__ import annotations

import pytest

from fuzzyengine import (
    DefinitionError,
    EvaluationError,
    FuzzyPipeline,
    FuzzySet,
    FuzzySystem,
    FuzzySystemBuilder,
    LinguisticVariable,
    Singleton,
    Triangular,
    Universe,
    membership_from_spec,
    parse_rule,
)


def test_singleton_output_off_the_sampling_grid_is_reported_not_silently_defaulted(
    vitesse: LinguisticVariable,
) -> None:
    narrow = LinguisticVariable("out", Universe(0, 10), (FuzzySet("spike", Singleton(3.33)),))
    system = (
        FuzzySystemBuilder("spiky")
        .add_input(vitesse)
        .add_output(narrow)
        .add_rule(parse_rule("SI vitesse EST rapide ALORS out EST spike"))
        .build()
    )
    result = system.evaluate({"vitesse": 90})
    assert result.fired_rules()[0].strength == 1.0
    assert result.outputs["out"] == 5.0
    assert any("ensemble de sortie vide" in w for w in result.warnings)


@pytest.mark.parametrize("bad", [float("inf"), float("-inf"), "fast", None, object()])
def test_non_finite_or_non_numeric_inputs_raise_evaluation_error(
    demo_system: FuzzySystem, bad: object
) -> None:
    with pytest.raises(EvaluationError):
        demo_system.evaluate({"vitesse": bad, "age": 20})  # type: ignore[dict-item]


@pytest.mark.parametrize(
    "params",
    [["a", "b", "c"], [0, True, 10], [0, float("nan"), 10], [None, 1, 2]],
)
def test_membership_factory_rejects_non_numeric_parameters(params: list[object]) -> None:
    with pytest.raises(DefinitionError, match="Paramètre non"):
        membership_from_spec("triangle", params)


def test_pipeline_rejects_stages_consuming_later_outputs(
    demo_system: FuzzySystem, score: LinguisticVariable
) -> None:
    verdict = LinguisticVariable(
        "verdict", Universe(0, 100), (FuzzySet("ok", Triangular(0, 50, 100)),)
    )
    final = (
        FuzzySystemBuilder("final")
        .add_input(score)
        .add_output(verdict)
        .add_rule(parse_rule("SI score EST bon ALORS verdict EST ok"))
        .build()
    )
    FuzzyPipeline("ordered", (demo_system, final))
    with pytest.raises(DefinitionError, match="étape ultérieure"):
        FuzzyPipeline("reversed", (final, demo_system))
