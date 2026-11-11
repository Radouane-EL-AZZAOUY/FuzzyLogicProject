"""Regression tests for the findings of the independent code review."""

from __future__ import annotations

import pytest

from fuzzyprolog import (
    Atom,
    DepthLimitError,
    Engine,
    ExecutionError,
    ProgramError,
    Settings,
    Var,
    parse_term,
    program_from_text,
    render,
)
from fuzzyprolog.terms import list_items

from .conftest import engine_for, solutions


def test_quoted_atoms_round_trip_through_render_and_parse() -> None:
    for name in ("it's", "O'Brien", "a\\b", "Route de rabat"):
        assert parse_term(render(Atom(name))) == Atom(name)
    assert render(Atom("it's")) == "'it''s'"


def test_anonymous_variable_never_aliases_a_user_variable() -> None:
    engine = engine_for("p(_1, _) :- _1 = a.")
    assert solutions(engine, "p(a, b).") == ["oui (1.00)"]
    assert solutions(engine, "p(b, b).") == []
    assert render(parse_term("f(_, _)")) == "f(_, _)"


def test_negation_is_sound_under_lambda_cut() -> None:
    program = program_from_text(":- lambda_cut(0.3).\na @ 0.2.\nb @ 0.9.")
    engine = Engine(program)
    assert solutions(engine, "\\+ a.") == ["oui (0.80)"]  # not 1.0: the sup ignores λ
    assert solutions(engine, "\\+ b.") == []  # 0.1 < λ : pruned as a result, not as a sup
    assert solutions(engine, "\\+ \\+ a.") == []  # 0.2 < λ
    unpruned = Engine(program, Settings(lambda_cut=0.0))
    assert solutions(unpruned, "\\+ \\+ a.") == ["oui (0.20)"]
    assert solutions(engine, "a.") == []  # the λ-cut still prunes direct answers


def test_findall_copies_the_template_with_fresh_variables() -> None:
    engine = engine_for("n(1). n(2).")
    solution = next(engine.query("findall(Z, n(_), L)."))
    items = list_items(solution.bindings["L"])
    assert items is not None and len(items) == 2
    assert all(isinstance(item, Var) for item in items)
    assert items[0] != items[1] and isinstance(solution.bindings["Z"], Var)
    assert solutions(engine, "findall(X-Y, (n(X), n(Y)), L), length(L, N).") == [
        "L = [1-1, 1-2, 2-1, 2-2], N = 4 (1.00)"
    ]


def test_numeric_similarity_is_rejected() -> None:
    with pytest.raises(ProgramError, match="par valeur"):
        program_from_text("1 ~ 2 @ 0.5.")


def test_non_callable_goals_and_overflow_are_engine_errors() -> None:
    engine = engine_for("q(1).")
    with pytest.raises(ExecutionError, match="non appelable"):
        list(engine.query("X = 1, X."))
    with pytest.raises(ExecutionError, match="non appelable"):
        list(engine.query("call(1)."))
    with pytest.raises(ExecutionError, match="arithmétique"):
        list(engine.query("X is 10.0 ** 400."))
    with pytest.raises(ProgramError, match="non appelable"):
        program_from_text("p :- 1.")


def test_second_argument_indexing_keeps_every_matching_clause() -> None:
    engine = engine_for("bloc(k1, a). bloc(k2, a). bloc(k1, b). bloc(K, c) :- K = k3.")
    assert solutions(engine, "bloc(K, a).") == ["K = k1 (1.00)", "K = k2 (1.00)"]
    assert solutions(engine, "bloc(K, c).") == ["K = k3 (1.00)"]
    assert len(solutions(engine, "bloc(K, X).")) == 4
    assert solutions(engine, "bloc(k1, X).") == ["X = a (1.00)", "X = b (1.00)"]
    assert solutions(engine, "bloc(k3, X).") == ["X = c (1.00)"]


def test_depth_limit_message_is_honest() -> None:
    engine = Engine(program_from_text(""), Settings(max_depth=50))
    long_list = "[" + ",".join(["x"] * 200) + "]"
    with pytest.raises(DepthLimitError, match="max_depth"):
        list(engine.query(f"long({long_list}, N)."))
