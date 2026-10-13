import pytest

from fuzzyengine import (
    PROBABILISTIC,
    Bisector,
    Centroid,
    DefinitionError,
    Interpretation,
    LinguisticVariable,
    MamdaniInference,
    MeanOfMaximum,
    RuleBase,
    Triangular,
    Universe,
    parse_rule,
)
from fuzzyengine.defuzzification import defuzzifier_from_name
from fuzzyengine.operators import ProductImplication


def test_centroid_of_symmetric_shapes_is_their_centre() -> None:
    u = Universe(0, 10)
    assert Centroid(resolution=1001).defuzzify(Triangular(2, 5, 8), u) == pytest.approx(5, abs=1e-6)
    assert Bisector(resolution=1001).defuzzify(Triangular(2, 5, 8), u) == pytest.approx(5, abs=0.02)
    assert MeanOfMaximum().defuzzify(Triangular(2, 5, 8), u) == pytest.approx(5, abs=0.02)


def test_centroid_of_clipped_triangle_moves_towards_the_wide_side() -> None:
    u = Universe(0, 10)
    clipped = lambda x: min(0.5, Triangular(0, 0, 10)(x))  # noqa: E731
    value = Centroid().defuzzify(clipped, u)
    assert 2.5 < value < 4.0


def test_empty_membership_is_signalled_with_none() -> None:
    u = Universe(0, 10)
    for method in (Centroid(), Bisector(), MeanOfMaximum()):
        assert method.defuzzify(lambda _x: 0.0, u) is None


def test_defuzzifier_factory() -> None:
    assert isinstance(defuzzifier_from_name("MOM"), MeanOfMaximum)
    assert defuzzifier_from_name("centroid", 101).resolution == 101  # type: ignore[attr-defined]
    with pytest.raises(DefinitionError):
        defuzzifier_from_name("median")
    with pytest.raises(DefinitionError):
        defuzzifier_from_name("centroid", 1)


def test_mamdani_activation_strengths_and_aggregation(
    vitesse: LinguisticVariable, age: LinguisticVariable, score: LinguisticVariable
) -> None:
    rules = RuleBase(
        (
            parse_rule("SI vitesse EST rapide ET age EST jeune ALORS score EST excellent", "R1"),
            parse_rule("SI vitesse EST lente ALORS score EST faible", "R2", weight=0.5),
        )
    )
    delta = Interpretation(
        {"vitesse": {"lente": 0.0, "moyenne": 0.2, "rapide": 0.6}, "age": {"jeune": 0.9}}
    )
    outcome = MamdaniInference().infer(rules, delta, {"score": score})
    r1, r2 = outcome.activations
    assert r1.antecedent_truth == pytest.approx(0.6) and r1.strength == pytest.approx(0.6)
    assert [a.degree for a in r1.atom_degrees] == [0.6, 0.9]
    assert r2.strength == 0.0 and not r2.fired and r1.fired
    distribution = outcome.distributions["score"]
    assert not distribution.is_empty
    # excellent clipped at 0.6 : plateau de la fonction = 0.6, hors support = 0
    assert distribution.membership(95) == pytest.approx(0.6)
    assert distribution.membership(10) == 0.0


def test_product_implication_scales_instead_of_clipping(score: LinguisticVariable) -> None:
    rules = RuleBase((parse_rule("SI v EST x ALORS score EST excellent", "R1"),))
    delta = Interpretation({"v": {"x": 0.5}})
    engine = MamdaniInference(PROBABILISTIC, implication=ProductImplication())
    distribution = engine.infer(rules, delta, {"score": score}).distributions["score"]
    assert distribution.membership(80) == pytest.approx(0.5 * score.term("excellent").degree(80))
