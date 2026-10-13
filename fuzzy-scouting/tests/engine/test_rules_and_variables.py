import pytest

from fuzzyengine import (
    Atom,
    Consequent,
    DefinitionError,
    FuzzySet,
    KnowledgeBaseError,
    LinguisticVariable,
    Rule,
    RuleBase,
    Triangular,
    Universe,
    parse_rule,
)


def test_variable_fuzzify_and_lookup(vitesse: LinguisticVariable) -> None:
    degrees = vitesse.fuzzify(65)
    assert degrees == pytest.approx({"lente": 0.0, "moyenne": 0.25, "rapide": 0.25})
    assert vitesse.labels == ("lente", "moyenne", "rapide")
    assert vitesse.has_term("rapide") and not vitesse.has_term("turbo")
    with pytest.raises(KnowledgeBaseError, match="turbo"):
        vitesse.term("turbo")


def test_variable_definition_errors() -> None:
    t = FuzzySet("a", Triangular(0, 1, 2))
    with pytest.raises(DefinitionError, match="deux fois"):
        LinguisticVariable("v", Universe(0, 2), (t, t))
    with pytest.raises(DefinitionError, match="au moins un terme"):
        LinguisticVariable("v", Universe(0, 2), ())
    with pytest.raises(DefinitionError):
        LinguisticVariable("", Universe(0, 2), (t,))
    with pytest.raises(DefinitionError):
        FuzzySet(" ", Triangular(0, 1, 2))


def test_fuzzyset_degree_is_clipped() -> None:
    class Wild:
        kind = "wild"

        def __call__(self, x: float) -> float:
            return 3.0

        def parameters(self) -> tuple[float, ...]:
            return ()

    assert FuzzySet("w", Wild()).degree(0) == 1.0  # type: ignore[arg-type]


def test_rule_invariants() -> None:
    atom = Atom("a", "x")
    with pytest.raises(KnowledgeBaseError, match="identifiant"):
        Rule("", atom, (Consequent("s", "y"),))
    with pytest.raises(KnowledgeBaseError, match="aucune conclusion"):
        Rule("R", atom, ())
    with pytest.raises(KnowledgeBaseError, match="poids"):
        Rule("R", atom, (Consequent("s", "y"),), weight=1.5)
    with pytest.raises(KnowledgeBaseError, match="poids"):
        Rule("R", atom, (Consequent("s", "y"),), weight=0)


def test_rulebase_rejects_duplicates_and_finds_rules() -> None:
    r1 = parse_rule("SI a EST x ALORS s EST y", "R1")
    with pytest.raises(KnowledgeBaseError, match="dupliqué"):
        RuleBase((r1, r1))
    base = RuleBase((r1,))
    assert len(base) == 1 and base.get("R1") is r1
    with pytest.raises(KnowledgeBaseError):
        base.get("R2")


def test_rulebase_validation_messages(
    vitesse: LinguisticVariable, score: LinguisticVariable
) -> None:
    inputs, outputs = {"vitesse": vitesse}, {"score": score}
    RuleBase((parse_rule("SI vitesse EST rapide ALORS score EST bon"),)).validate(inputs, outputs)
    cases = {
        "SI acceleration EST rapide ALORS score EST bon": "variable d'entrée inconnue",
        "SI vitesse EST turbo ALORS score EST bon": "terme inconnu 'turbo'",
        "SI vitesse EST rapide ALORS note EST bon": "variable de sortie inconnue 'note'",
        "SI vitesse EST rapide ALORS score EST parfait": "terme inconnu 'parfait'",
    }
    for text, fragment in cases.items():
        with pytest.raises(KnowledgeBaseError, match=fragment):
            RuleBase((parse_rule(text, "X"),)).validate(inputs, outputs)
