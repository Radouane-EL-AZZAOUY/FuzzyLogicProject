import pytest

from fuzzyengine import (
    FRENCH,
    PROBABILISTIC,
    ZADEH,
    And,
    Atom,
    EvaluationError,
    Interpretation,
    Not,
    Or,
)
from fuzzyengine.formulas import conjunction
from fuzzyengine.modifiers import Somewhat, Very, modifier_from_name


@pytest.fixture
def delta() -> Interpretation:
    return Interpretation({"p": {"x": 0.8}, "q": {"y": 0.3}, "r": {"z": 0.6}})


def test_atom_truth_and_missing_atom(delta: Interpretation) -> None:
    assert Atom("p", "x").truth(delta, ZADEH) == 0.8
    with pytest.raises(EvaluationError):
        Atom("p", "unknown").truth(delta, ZADEH)


def test_connectives_follow_the_operator_family(delta: Interpretation) -> None:
    f = And(Atom("p", "x"), Or(Atom("q", "y"), Not(Atom("r", "z"))))
    # Zadeh : min(0.8, max(0.3, 0.4)) = 0.4
    assert f.truth(delta, ZADEH) == pytest.approx(0.4)
    # Probabiliste : 0.8 * (0.3 + 0.4 - 0.12) = 0.464
    assert f.truth(delta, PROBABILISTIC) == pytest.approx(0.464)


def test_modifiers_concentrate_or_dilate(delta: Interpretation) -> None:
    assert Atom("p", "x", Very()).truth(delta, ZADEH) == pytest.approx(0.64)
    assert Atom("p", "x", Somewhat()).truth(delta, ZADEH) == pytest.approx(0.8**0.5)
    assert modifier_from_name("très").name == "very"
    assert modifier_from_name("plutôt").name == "somewhat"


def test_rendering_follows_course_parenthesis_rules() -> None:
    p, q, r = Atom("p", "x"), Atom("q", "y"), Atom("r", "z")
    # (¬(p)) ∧ (q) devient ¬p ∧ q
    assert str(And(Not(p), q)) == "p IS NOT x AND q IS y"
    # ((¬p) ∧ q) ∨ r : pas de parenthèses nécessaires (∧ prioritaire sur ∨)
    assert str(Or(And(Not(p), q), r)) == "p IS NOT x AND q IS y OR r IS z"
    # ¬p ∧ (q ∨ r) : les parenthèses sont conservées
    assert str(And(Not(p), Or(q, r))) == "p IS NOT x AND (q IS y OR r IS z)"
    # ¬(p ∧ q) : la négation d'une formule composée garde ses parenthèses
    assert str(Not(And(p, q))) == "NOT (p IS x AND q IS y)"


def test_french_rendering() -> None:
    f = And(Not(Atom("vitesse", "rapide", Very())), Atom("age", "jeune"))
    assert f.render(FRENCH) == "vitesse N'EST PAS très rapide ET age EST jeune"


def test_atoms_enumeration_and_conjunction_helper() -> None:
    p, q, r = Atom("p", "x"), Atom("q", "y"), Atom("r", "z")
    f = conjunction(p, q, r)
    assert [a.variable for a in f.atoms()] == ["p", "q", "r"]
    assert str(f) == "p IS x AND q IS y AND r IS z"
    with pytest.raises(ValueError):
        conjunction()


def test_interpretation_export(delta: Interpretation) -> None:
    assert delta.variables() == ("p", "q", "r")
    assert delta.as_dict()["q"] == {"y": 0.3}
