"""Graded resolution: degrees, similarities, λ-cut, negation, explanations."""

import pytest

from fuzzyprolog import (
    Atom,
    DepthLimitError,
    Engine,
    ExecutionError,
    InstantiationError,
    Program,
    ProgramError,
    Settings,
    program_from_text,
)
from fuzzyprolog.tnorms import Product

from .conftest import engine_for, solutions


def test_fact_and_rule_degrees_combine_with_the_t_norm(flou: Engine) -> None:
    assert solutions(flou, "aime(ali, foot).") == ["oui (0.80)"]
    assert solutions(flou, "passionne(ali).") == ["oui (0.80)"]  # min(0.9, 0.8)
    product = Engine(flou.program, Settings(tnorm=Product()))
    assert next(product.query("passionne(ali).")).degree == pytest.approx(0.72)


def test_similarity_unification_in_clause_heads_is_transitive(flou: Engine) -> None:
    # "Mohamed" ~ "Mohammed" 0.9 and "Mohammed" ~ "Muhammad" 0.8 => "Mohamed" ~ "Muhammad" 0.8
    assert solutions(flou, "meme_prenom(p1, p2).") == ["oui (0.80)"]
    assert solutions(flou, "meme_prenom(p1, p3).") == ["oui (1.00)"]
    assert solutions(flou, "meme_ville(p1, p2).") == ["oui (0.95)"]
    assert solutions(flou, "doublon(A, B).") == ["A = p1, B = p2 (0.80)"]
    assert solutions(flou, 'X = "Mohamed", X = "Muhammad".') == ['X = "Mohamed" (0.80)']
    assert solutions(flou, "casablanca = casa.") == ["oui (0.95)"]
    assert solutions(flou, "casablanca \\= casa.") == []
    assert solutions(flou, "casablanca \\= rabat.") == ["oui (1.00)"]


def test_lambda_cut_prunes_weak_derivations(flou: Engine) -> None:
    strict = Engine(flou.program, Settings(lambda_cut=0.85))
    assert solutions(strict, "doublon(A, B).") == []
    assert solutions(strict, "meme_prenom(p1, p3).") == ["oui (1.00)"]
    directive = program_from_text(":- lambda_cut(0.5).\naime(x, y) @ 0.4.\naime(x, z) @ 0.6.")
    assert solutions(Engine(directive), "aime(x, W).") == ["W = z (0.60)"]


def test_graded_negation_is_one_minus_the_best_degree(flou: Engine) -> None:
    assert solutions(flou, "\\+ aime(ali, lecture).") == ["oui (0.70)"]
    assert solutions(flou, "\\+ aime(ali, cinema).") == ["oui (1.00)"]
    assert solutions(flou, "\\+ meme_prenom(p1, p3).") == []


def test_graded_builtins_and_degree_introspection(flou: Engine) -> None:
    assert solutions(flou, "similar(casablanca, casa, D).") == ["D = 0.95 (1.00)"]
    assert solutions(flou, "similar(casablanca, rabat, D).") == ["D = 0.0 (1.00)"]
    assert solutions(flou, "with_degree(doublon(A, B), D).") == ["A = p1, B = p2, D = 0.8 (0.80)"]
    assert solutions(flou, "best_degree(aime(ali, _), D).") == ["D = 0.8 (1.00)"]
    assert solutions(flou, "best_degree(aime(sam, _), D).") == ["D = 0.0 (1.00)"]
    text = next(flou.query('text_similar("El Amrani", "Lamrani").'))
    assert 0.85 < text.degree < 1.0
    assert solutions(flou, "number_close(10, 12, 10).") == ["oui (0.80)"]
    assert solutions(flou, "number_close(10, 30, 10).") == []
    assert next(flou.query('jaro_winkler("abc", "abc", D).')).bindings["D"].value == 1.0  # type: ignore[union-attr]


def test_explanation_lists_steps_similarities_and_degrees(flou: Engine) -> None:
    solution = next(flou.query("doublon(A, B)."))
    text = solution.explain()
    assert text.startswith("A = p1, B = p2 (0.80)")
    assert (
        "clause l.13 : doublon(A, B) :- meme_prenom(A, B), meme_ville(A, B), A @< B @ 0.9." in text
    )
    assert 'similarité "Mohamed" ~ "Muhammad" (0.80)' in text
    assert "similarité casablanca ~ casa (0.95)" in text
    assert "prédéfini @</2" in text
    levels = [step.level for step in solution.steps]
    assert levels == [0, 1, 2, 2, 1, 2, 2, 1]
    quiet = Engine(flou.program, trace=False)
    assert next(quiet.query("doublon(A, B).")).steps == ()


def test_control_constructs() -> None:
    engine = engine_for("a(1). a(2). b(2). c :- a(X), b(X), !.")
    assert solutions(engine, "(a(X) ; b(X)).") == ["X = 1 (1.00)", "X = 2 (1.00)", "X = 2 (1.00)"]
    assert solutions(engine, "(a(3) -> R = oui ; R = non).") == ["R = non (1.00)"]
    assert solutions(engine, "(a(X) -> R = X ; R = non).") == ["X = 1, R = 1 (1.00)"]
    assert solutions(engine, "(a(X), X > 1 -> R = X).") == ["X = 2, R = 2 (1.00)"]
    assert solutions(engine, "call(a, X).") == ["X = 1 (1.00)", "X = 2 (1.00)"]
    assert solutions(engine, "call((a(X), !)).") == ["X = 1 (1.00)"]  # cut is local to call/1
    assert solutions(engine, "findall(X, a(X), L).") == ["L = [1, 2] (1.00)"]
    assert solutions(engine, "findall(X-Y, (a(X), b(Y)), L).") == ["L = [1-2, 2-2] (1.00)"]
    assert solutions(engine, "c.") == ["oui (1.00)"]
    assert solutions(engine, "true, \\+ fail.") == ["oui (1.00)"]
    assert solutions(engine, "a(X), !, X = 2.") == []  # cut in the query commits to X = 1


def test_arithmetic_comparison_and_type_builtins() -> None:
    engine = engine_for("")
    assert solutions(
        engine, "X is 7 // 2, Y is 7 mod 2, Z is 2 ** 3, W is abs(-4) + max(1, 5)."
    ) == ["X = 3, Y = 1, Z = 8, W = 9 (1.00)"]
    assert solutions(engine, "3 < 4, 4 >= 4, 2 =:= 2.0, 1 =\\= 2, 1 + 1 =< 2.") == ["oui (1.00)"]
    assert solutions(engine, "a @< b, 1 @< a, f(a) @> z, compare(O, 2, 1).") == ["O = > (1.00)"]
    assert solutions(
        engine, 'var(X), nonvar(a), atom(a), number(1), string("s"), is_list([a]), compound(f(x)).'
    ) == ["oui (1.00)"]
    assert solutions(
        engine, 'string_lower("ABC", L), string_length("abcd", N), string_concat("a", "b", C).'
    ) == ['L = "abc", N = 4, C = "ab" (1.00)']
    assert solutions(engine, 'atom_string(A, "x"), atom_string(y, S).') == ['A = x, S = "y" (1.00)']
    assert solutions(engine, "msort([c, a, b], L).") == ["L = [a, b, c] (1.00)"]
    assert solutions(engine, "X = f(Y), X == f(Y), X \\== f(z).") == ["X = f(Y) (1.00)"]


def test_runtime_errors_are_explicit() -> None:
    engine = engine_for("boucle :- boucle.")
    with pytest.raises(DepthLimitError):
        list(engine.query("boucle."))
    with pytest.raises(ExecutionError, match="Prédicat inconnu : inconnu/1"):
        list(engine.query("inconnu(x)."))
    with pytest.raises(InstantiationError):
        list(engine.query("X is Y + 1."))
    with pytest.raises(InstantiationError):
        list(engine.query("call(X)."))
    with pytest.raises(ExecutionError, match="Division par zéro"):
        list(engine.query("X is 1 / 0."))
    with pytest.raises(ProgramError, match="Degré"):
        program_from_text("p(a) @ 1.5.")
    with pytest.raises(ProgramError, match="connecteur"):
        program_from_text("','(a, b).")
    with pytest.raises(ProgramError, match="Directive inconnue"):
        program_from_text(":- magie(1).")


def test_query_limit_and_output_builtins(capsys: pytest.CaptureFixture[str]) -> None:
    engine = engine_for("n(1). n(2). n(3).")
    assert len(list(engine.query("n(X).", limit=2))) == 2
    assert solutions(engine, 'write("salut"), nl, writeln(f(x)).') == ["oui (1.00)"]
    assert capsys.readouterr().out == "salut\nf(x)\n"


def test_program_api_and_first_argument_indexing() -> None:
    program: Program = program_from_text("f(a, 1). f(b, 2). f(X, 3). g(1).", prelude=False)
    assert program.predicates() == ["f/2", "g/1"]
    assert len(program) == 4
    engine = Engine(program)
    assert solutions(engine, "f(b, N).") == [
        "N = 2 (1.00)",
        "N = 3 (1.00)",
    ]  # indexed + variable-headed clause
    assert solutions(engine, "f(Z, 1).") == ["Z = a (1.00)"]
    directives = program_from_text(
        ":- tnorm(product).\n:- max_depth(50).\n:- occurs_check(false).\n:- similar(a, b, 0.5)."
    )
    assert directives.settings.tnorm.name == "product" and directives.settings.max_depth == 50
    assert directives.settings.occurs_check is False
    assert directives.similarity.degree(Atom("a"), Atom("b")) == 0.5
