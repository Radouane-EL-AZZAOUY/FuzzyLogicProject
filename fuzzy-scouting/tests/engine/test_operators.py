"""The fuzzy connectives must extend the course's truth tables conservatively."""

from itertools import product

import pytest

from fuzzyengine import LUKASIEWICZ, PROBABILISTIC, ZADEH, DefinitionError, FuzzyOperators
from fuzzyengine.operators import (
    MinimumImplication,
    ProductImplication,
    aggregation_from_name,
    implication_from_name,
    operators_from_name,
)

FAMILIES = [ZADEH, PROBABILISTIC, LUKASIEWICZ]

# Truth tables of the course (page « Tables de vérité des opérateurs binaires usuels »).
CLASSICAL_AND = {(0, 0): 0, (0, 1): 0, (1, 0): 0, (1, 1): 1}
CLASSICAL_OR = {(0, 0): 0, (0, 1): 1, (1, 0): 1, (1, 1): 1}


@pytest.mark.parametrize("ops", FAMILIES, ids=lambda o: o.name)
def test_restricted_to_binary_values_every_family_matches_the_classical_tables(
    ops: FuzzyOperators,
) -> None:
    for p, q in product((0, 1), repeat=2):
        assert ops.conjunction(p, q) == CLASSICAL_AND[(p, q)]
        assert ops.disjunction(p, q) == CLASSICAL_OR[(p, q)]
    assert ops.negation(0) == 1 and ops.negation(1) == 0


@pytest.mark.parametrize("ops", FAMILIES, ids=lambda o: o.name)
def test_commutativity_and_neutral_elements(ops: FuzzyOperators) -> None:
    for a, b in product((0.0, 0.3, 0.7, 1.0), repeat=2):
        assert ops.conjunction(a, b) == pytest.approx(ops.conjunction(b, a))
        assert ops.disjunction(a, b) == pytest.approx(ops.disjunction(b, a))
        # éléments neutres du cours : F ∧ ■ ↔ F et F ∨ □ ↔ F
        assert ops.conjunction(a, 1.0) == pytest.approx(a)
        assert ops.disjunction(a, 0.0) == pytest.approx(a)


def test_de_morgan_holds_for_zadeh_operators() -> None:
    for a, b in product((0.0, 0.2, 0.5, 0.9, 1.0), repeat=2):
        lhs = ZADEH.negation(ZADEH.disjunction(a, b))
        rhs = ZADEH.conjunction(ZADEH.negation(a), ZADEH.negation(b))
        assert lhs == pytest.approx(rhs)


def test_excluded_middle_is_lost_in_fuzzy_logic() -> None:
    """In the course ⊢ F ∨ ¬F ; with graded truth it only holds for crisp values."""
    assert ZADEH.disjunction(1.0, ZADEH.negation(1.0)) == 1.0
    assert ZADEH.disjunction(0.5, ZADEH.negation(0.5)) == 0.5  # ≠ 1 !
    # ... except for the Łukasiewicz family, which keeps it (bounded sum).
    assert LUKASIEWICZ.disjunction(0.5, LUKASIEWICZ.negation(0.5)) == 1.0


def test_implications() -> None:
    assert MinimumImplication()(0.3, 0.8) == 0.3
    assert ProductImplication()(0.5, 0.8) == pytest.approx(0.4)
    assert implication_from_name("product").name == "product"
    assert aggregation_from_name("max")(0.2, 0.7) == 0.7
    assert operators_from_name("ZADEH") is ZADEH


def test_unknown_names_raise() -> None:
    with pytest.raises(DefinitionError):
        operators_from_name("boolean")
    with pytest.raises(DefinitionError):
        implication_from_name("kleene")
    with pytest.raises(DefinitionError):
        aggregation_from_name("mean")
