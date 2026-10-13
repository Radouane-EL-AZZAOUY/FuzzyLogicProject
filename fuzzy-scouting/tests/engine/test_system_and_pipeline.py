import pytest

from fuzzyengine import (
    DefinitionError,
    EvaluationError,
    FuzzyPipeline,
    FuzzySystem,
    FuzzySystemBuilder,
    LinguisticVariable,
    Universe,
    explain_pipeline,
    explain_result,
    parse_rule,
)


def test_evaluation_is_monotonic_and_labelled(demo_system: FuzzySystem) -> None:
    slow = demo_system.evaluate({"vitesse": 10, "age": 30})
    medium = demo_system.evaluate({"vitesse": 50, "age": 30})
    fast = demo_system.evaluate({"vitesse": 90, "age": 30})
    fast_young = demo_system.evaluate({"vitesse": 90, "age": 20})
    scores = [r.outputs["score"] for r in (slow, medium, fast, fast_young)]
    assert scores == sorted(scores)
    assert slow.label("score") == "faible"
    assert medium.label("score") == "moyen"
    assert fast.label("score") == "bon"
    assert fast_young.label("score") == "excellent"
    assert fast_young.fired_rules()[0].rule.identifier == "R1"


def test_out_of_universe_inputs_are_clamped_with_a_warning(demo_system: FuzzySystem) -> None:
    result = demo_system.evaluate({"vitesse": 250, "age": 12})
    assert result.inputs == {"vitesse": 100, "age": 16}
    assert len(result.warnings) == 2 and "hors de l'univers" in result.warnings[0]


def test_missing_or_nan_input_raises(demo_system: FuzzySystem) -> None:
    with pytest.raises(EvaluationError, match="manquante"):
        demo_system.evaluate({"vitesse": 10})
    with pytest.raises(EvaluationError, match="NaN"):
        demo_system.evaluate({"vitesse": float("nan"), "age": 20})


def test_extra_inputs_are_ignored(demo_system: FuzzySystem) -> None:
    result = demo_system.evaluate({"vitesse": 50, "age": 30, "autre": 1})
    assert "autre" not in result.inputs


def test_no_rule_fired_gives_default_with_warning(
    vitesse: LinguisticVariable, score: LinguisticVariable
) -> None:
    system = (
        FuzzySystemBuilder("sparse")
        .add_input(vitesse)
        .add_output(score)
        .add_rule(parse_rule("SI vitesse EST rapide ALORS score EST bon"))
        .build()
    )
    result = system.evaluate({"vitesse": 0})
    assert result.outputs["score"] == 50.0
    assert any("Aucune règle" in w for w in result.warnings)
    assert result.fired_rules() == []


def test_system_definition_errors(vitesse: LinguisticVariable, score: LinguisticVariable) -> None:
    with pytest.raises(DefinitionError, match="au moins une entrée"):
        FuzzySystemBuilder("x").add_input(vitesse).build()
    with pytest.raises(DefinitionError, match="à la fois"):
        FuzzySystemBuilder("x").add_input(vitesse).add_output(vitesse).build()
    with pytest.raises(DefinitionError, match="nom"):
        FuzzySystemBuilder(" ").add_input(vitesse).add_output(score).build()
    with pytest.raises(DefinitionError, match="clé"):
        FuzzySystem("x", {"v": vitesse}, {"score": score}, rule_base=_empty_rules())


def _empty_rules():  # type: ignore[no-untyped-def]
    from fuzzyengine import RuleBase

    return RuleBase(())


def test_pipeline_chains_outputs_into_inputs(
    demo_system: FuzzySystem, score: LinguisticVariable
) -> None:
    verdict = LinguisticVariable("verdict", Universe(0, 100), score.terms)
    final = (
        FuzzySystemBuilder("final")
        .add_input(score)
        .add_output(verdict)
        .add_rule(parse_rule("SI score EST excellent OU score EST bon ALORS verdict EST excellent"))
        .add_rule(
            parse_rule("SI score EST faible OU score EST moyen ALORS verdict EST faible", "F2")
        )
        .build()
    )
    pipeline = FuzzyPipeline("demo", (demo_system, final))
    assert pipeline.required_inputs == ("vitesse", "age")
    assert pipeline.produced_outputs == ("score", "verdict")
    assert pipeline.final_outputs == ("verdict",)
    result = pipeline.evaluate({"vitesse": 90, "age": 20})
    assert result.labels == {"score": "excellent", "verdict": "excellent"}
    assert result.stage("final").inputs["score"] == pytest.approx(result.outputs["score"])
    assert result.warnings == ()
    with pytest.raises(KeyError):
        result.stage("missing")
    text = explain_pipeline(result)
    assert "Système « demo »" in text and "Système « final »" in text


def test_pipeline_definition_errors(demo_system: FuzzySystem) -> None:
    with pytest.raises(DefinitionError, match="au moins une étape"):
        FuzzyPipeline("p", ())
    with pytest.raises(DefinitionError, match="deux fois"):
        FuzzyPipeline("p", (demo_system, demo_system))


def test_explanation_mentions_rules_inputs_and_labels(demo_system: FuzzySystem) -> None:
    text = explain_result(demo_system.evaluate({"vitesse": 90, "age": 20}))
    assert "[R1] force=1.00" in text
    assert "vitesse = 90" in text
    assert "score = " in text and "excellent" in text
    assert text.isascii() or all(ord(ch) < 0x2000 or ch in "«»" for ch in text)
