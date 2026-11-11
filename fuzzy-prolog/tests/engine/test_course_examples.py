"""The engine must reproduce the behaviour described in the course slides."""

from fuzzyprolog import Engine

from .conftest import NEGATION_ET_RECURSION, engine_for, solutions


def test_p73_questions_on_facts(famille: Engine) -> None:
    assert famille.succeeds("masculin(ali).")
    assert (
        not famille.succeeds("masculin(jawad).") if famille.program.defines("masculin/1") else True
    )


def test_p75_rules_fils_parent_grand_parent_ancetre(famille: Engine) -> None:
    assert solutions(famille, "fils(X, ali).") == ["X = mohamed (1.00)"]
    assert solutions(famille, "fils(ali, X).") == ["X = aicha (1.00)"]
    assert solutions(famille, "grand_parent(X, Y).") == [
        "X = ali, Y = youssef (1.00)",
        "X = aicha, Y = mohamed (1.00)",
    ]
    assert solutions(famille, "ancetre(aicha, X).") == [
        "X = ali (1.00)",
        "X = fatima (1.00)",
        "X = mohamed (1.00)",
        "X = youssef (1.00)",
    ]


def test_p77_list_predicates_from_the_prelude(famille: Engine) -> None:
    assert solutions(famille, "app(b, [a, b, c]).") == ["oui (1.00)"]
    assert solutions(famille, "app(X, [a, b]).") == ["X = a (1.00)", "X = b (1.00)"]
    assert solutions(famille, "long([a, b, c], N).") == ["N = 3 (1.00)"]
    # the course's intersection has no cut: it enumerates every sub-intersection
    assert solutions(famille, "intersection([a, b, c], [c, a], L).") == [
        "L = [a, c] (1.00)",
        "L = [a] (1.00)",
        "L = [c] (1.00)",
        "L = [] (1.00)",
    ]
    assert solutions(famille, "append(X, Y, [1, 2]).") == [
        "X = [], Y = [1, 2] (1.00)",
        "X = [1], Y = [2] (1.00)",
        "X = [1, 2], Y = [] (1.00)",
    ]


def test_p78_p80_search_tree_finds_aicha_through_r2(humeur: Engine) -> None:
    found = list(humeur.query("est_de_bonne_humeur(X)."))
    assert [str(s) for s in found] == ["X = aicha (1.00)"]
    # The proof shows R2 (second clause, line 3) was the rule used, after R1 failed.
    first = found[0].steps[0]
    assert "clause l.3" in first.via and "reussit_dans_le_travail" in first.via
    assert [s.level for s in found[0].steps] == [0, 1, 1]


def test_p81_negation_as_failure() -> None:
    engine = engine_for(NEGATION_ET_RECURSION)
    assert solutions(engine, "fort(X).") == ["X = ali (1.00)"]
    assert solutions(engine, "\\+ petit(ali).") == ["oui (1.00)"]
    assert solutions(engine, "\\+ petit(sam).") == []


def test_p83_cut_solution_counts(coupe: Engine) -> None:
    """p(X,Y) :- q(X), r(X,Y).      6 solutions
    p(X,Y) :- q(X), r(X,Y), !.   1 solution
    p(X,Y) :- q(X), !, r(X,Y).   3 solutions
    p(X,Y) :- !, q(X), r(X,Y).   5 solutions"""
    counts = {p: len(list(coupe.query(f"{p}(X, Y)."))) for p in ("p1", "p2", "p3", "p4")}
    assert counts == {"p1": 6, "p2": 1, "p3": 3, "p4": 5}
    assert solutions(coupe, "p2(X, Y).") == ["X = a, Y = a1 (1.00)"]
    assert "X = d, Y = d1 (1.00)" in solutions(coupe, "p1(X, Y).")
    assert "X = d, Y = d1 (1.00)" not in solutions(coupe, "p4(X, Y).")


def test_p84_recursion_factorial() -> None:
    engine = engine_for(NEGATION_ET_RECURSION)
    assert solutions(engine, "factoriel(5, F).") == ["F = 120 (1.00)"]
    assert solutions(engine, "factoriel(1, F).") == ["F = 1 (1.00)"]


def test_prolog_search_order_is_depth_first_left_to_right(famille: Engine) -> None:
    # parent/2 tries pere/2 clauses first, then mere/2 : the answer order proves it.
    assert solutions(famille, "parent(X, Y).") == [
        "X = ali, Y = mohamed (1.00)",
        "X = mohamed, Y = youssef (1.00)",
        "X = aicha, Y = ali (1.00)",
        "X = aicha, Y = fatima (1.00)",
    ]
