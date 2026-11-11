import pytest

from fuzzyprolog import (
    Atom,
    Number,
    ParseError,
    String,
    Struct,
    Var,
    parse_query,
    parse_term,
    render,
)
from fuzzyprolog.parser import Kind, parse_program_items, tokenize
from fuzzyprolog.terms import EMPTY_LIST, list_items, make_list


def test_tokenizer_distinguishes_end_dots_symbols_comments_and_quotes() -> None:
    tokens = tokenize("a :- b. % commentaire\n'Route de rabat' = \"txt\". /* bloc */ X =.. Y.")
    kinds = [(t.kind, t.text) for t in tokens]
    assert (Kind.ATOM, ":-") in kinds
    assert kinds.count((Kind.END, ".")) == 3
    assert (Kind.ATOM, "Route de rabat") in kinds
    assert (Kind.STRING, "txt") in kinds
    assert (Kind.ATOM, "=..") in kinds
    assert kinds[-1][0] is Kind.EOF


def test_functional_notation_flag_and_numbers() -> None:
    tokens = tokenize("f(1, 2.5, 3e2) f (x)")
    assert tokens[0].functional and not tokens[7].functional
    assert [t.text for t in tokens if t.kind is Kind.NUMBER] == ["1", "2.5", "3e2"]


def test_parse_terms_lists_and_strings() -> None:
    term = parse_term("f(a, [1, 2 | T], \"nom\", 'Quoted atom', _)")
    assert isinstance(term, Struct) and term.functor == "f" and term.arity == 5
    assert term.args[0] == Atom("a")
    assert term.args[2] == String("nom") and term.args[3] == Atom("Quoted atom")
    items = list_items(parse_term("[a, b, c]"))
    assert items == [Atom("a"), Atom("b"), Atom("c")]
    assert parse_term("[]") == EMPTY_LIST
    assert render(make_list([Atom("a")], Var("T"))) == "[a | T]"


def test_operator_precedence_follows_prolog() -> None:
    assert render(parse_term("X is 1 + 2 * 3")) == "X is 1+2*3"
    assert parse_term("1 + 2 * 3") == Struct("+", (Number(1), Struct("*", (Number(2), Number(3)))))
    assert parse_term("(1 + 2) * 3") == Struct(
        "*", (Struct("+", (Number(1), Number(2))), Number(3))
    )
    assert parse_term("1 - 2 - 3") == Struct("-", (Struct("-", (Number(1), Number(2))), Number(3)))
    clause = parse_term("a :- b, c ; d")
    assert clause == Struct(
        ":-", (Atom("a"), Struct(";", (Struct(",", (Atom("b"), Atom("c"))), Atom("d"))))
    )
    assert parse_term("\\+ p(X)") == Struct("\\+", (Struct("p", (Var("X"),)),))
    assert parse_term("- 3") == Number(-3) and parse_term("X = -Y") == Struct(
        "=", (Var("X"), Struct("-", (Var("Y"),)))
    )
    assert parse_term("A @< B") == Struct("@<", (Var("A"), Var("B")))
    assert parse_term("f(a, (b, c))") == Struct(
        "f", (Atom("a"), Struct(",", (Atom("b"), Atom("c"))))
    )


def test_variables_are_shared_within_a_clause_and_anonymous_ones_are_distinct() -> None:
    term = parse_term("f(X, X, _, _)")
    assert isinstance(term, Struct)
    assert term.args[0] is term.args[1] or term.args[0] == term.args[1]
    assert term.args[2] != term.args[3]


def test_program_items_degrees_similarities_directives() -> None:
    items = parse_program_items(
        'pere(ali, mohamed).\nq(X) :- r(X) @ 0.7.\n"a" ~ "b" @ 0.9.\n:- lambda_cut(0.5).\n'
    )
    assert [i.degree for i in items] == [1.0, 0.7, 0.9, 1.0]
    assert [i.line for i in items] == [1, 2, 3, 4]
    assert isinstance(items[3].term, Struct) and items[3].term.functor == ":-"


def test_parse_query_flattens_conjunctions() -> None:
    goals = parse_query("a, (b, c), d.")
    assert [render(g) for g in goals] == ["a", "b", "c", "d"]


@pytest.mark.parametrize(
    ("text", "fragment"),
    [
        ("f(a", r"'\)' attendu"),
        ("a :- b. c :- d", "'.' attendu"),
        ('"non terminée', "non terminé"),
        ("p(X) @ x.", "Degré"),
        ("[a, b", r"'\]' attendu"),
        ("", "vide"),
        ("a. b c.", "'.' attendu"),
    ],
)
def test_syntax_errors_locate_the_problem(text: str, fragment: str) -> None:
    with pytest.raises(ParseError, match=fragment):
        if "." in text:
            parse_program_items(text)
        else:
            parse_query(text)


def test_render_quotes_when_needed() -> None:
    assert render(Atom("Route de rabat")) == "'Route de rabat'"
    assert render(String('a"b')) == '"a\\"b"'
    assert render(Struct("-", (Var("X"),))) == "- X"
    assert render(parse_term("a :- b, c")) == "a :- b, c"
