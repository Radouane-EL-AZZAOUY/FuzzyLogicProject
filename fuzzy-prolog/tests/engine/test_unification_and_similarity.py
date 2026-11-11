"""Unification and substitutions, checked against the course's own examples."""

import pytest

from fuzzyprolog import (
    EMPTY,
    Atom,
    Number,
    ProgramError,
    SimilarityRelation,
    String,
    Substitution,
    Var,
    parse_term,
    unify,
)
from fuzzyprolog.tnorms import Product


def test_course_example_p55_most_general_unifier() -> None:
    """A1 : P(X,Z)   A2 : P(f(Y),g(a))   σ = {X|f(Y), Z|g(a)}."""
    a1, a2 = parse_term("p(X, Z)"), parse_term("p(f(Y), g(a))")
    unifier = unify(a1, a2, EMPTY)
    assert unifier is not None and unifier.degree == 1.0
    sigma = unifier.substitution
    assert sigma.resolve(a1) == sigma.resolve(a2) == parse_term("p(f(Y), g(a))")
    assert sigma.resolve(Var("X")) == parse_term("f(Y)") and sigma.resolve(Var("Z")) == parse_term(
        "g(a)"
    )


def test_course_example_p54_substitution_application() -> None:
    """A : P(U) → R(X)   σ = {(X|f(a)), (U|f(X))}   A σ : P(f(f(a))) → R(f(a))."""
    a = parse_term("implique(p(U), r(X))")
    sigma = Substitution().bind(Var("X"), parse_term("f(a)")).bind(Var("U"), parse_term("f(X)"))
    assert sigma.resolve(a) == parse_term("implique(p(f(f(a))), r(f(a)))")


def test_occurs_check_rejects_x_equals_f_x() -> None:
    assert unify(Var("X"), parse_term("f(X)"), EMPTY) is None
    assert unify(Var("X"), parse_term("f(X)"), EMPTY, occurs_check=False) is not None


def test_classical_failures() -> None:
    assert unify(Atom("a"), Atom("b"), EMPTY) is None
    assert unify(parse_term("f(a)"), parse_term("g(a)"), EMPTY) is None
    assert unify(parse_term("f(a)"), parse_term("f(a, b)"), EMPTY) is None
    assert unify(Atom("a"), String("a"), EMPTY) is None
    assert unify(Number(1), Number(1.0), EMPTY) is not None
    assert unify(Number(1), Number(2), EMPTY) is None


def test_similarity_based_unification_degrees() -> None:
    relation = SimilarityRelation()
    relation.declare(Atom("a"), Atom("b"), 0.7)
    unifier = unify(parse_term("f(a, X)"), parse_term("f(b, c)"), EMPTY, relation)
    assert unifier is not None and unifier.degree == pytest.approx(0.7)
    assert unifier.similarities == ((Atom("a"), Atom("b"), 0.7),)
    assert unifier.substitution.resolve(Var("X")) == Atom("c")
    # two similar pairs : min by default, product with another t-norm
    relation.declare(Atom("c"), Atom("d"), 0.5)
    u_min = unify(parse_term("f(a, c)"), parse_term("f(b, d)"), EMPTY, relation)
    u_prod = unify(parse_term("f(a, c)"), parse_term("f(b, d)"), EMPTY, relation, tnorm=Product())
    assert u_min is not None and u_min.degree == pytest.approx(0.5)
    assert u_prod is not None and u_prod.degree == pytest.approx(0.35)
    # threshold prunes weak unifications
    assert (
        unify(parse_term("f(a, c)"), parse_term("f(b, d)"), EMPTY, relation, threshold=0.6) is None
    )


def test_similarity_relation_is_reflexive_symmetric_and_max_min_transitive() -> None:
    relation = SimilarityRelation()
    relation.declare(Atom("a"), Atom("b"), 0.9)
    relation.declare(Atom("b"), Atom("c"), 0.8)
    relation.declare(Atom("a"), Atom("c"), 0.5)  # weaker than the path through b
    assert relation.degree(Atom("a"), Atom("a")) == 1.0
    assert relation.degree(Atom("b"), Atom("a")) == pytest.approx(0.9)
    assert relation.degree(Atom("a"), Atom("c")) == pytest.approx(0.8)
    assert relation.degree(Atom("a"), Atom("z")) == 0.0
    relation.transitive = False
    relation.declare(Atom("x"), Atom("y"), 0.4)  # invalidates the closure
    assert relation.degree(Atom("a"), Atom("c")) == pytest.approx(0.5)


def test_similarity_declaration_errors() -> None:
    relation = SimilarityRelation()
    with pytest.raises(ProgramError, match="constantes"):
        relation.declare(parse_term("f(a)"), Atom("b"), 0.5)
    with pytest.raises(ProgramError, match="hors"):
        relation.declare(Atom("a"), Atom("b"), 1.5)
