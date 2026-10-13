import pytest

from fuzzyengine import FRENCH, And, Atom, Not, Or, ParseError, parse_formula, parse_rule
from fuzzyengine.dsl import TokenType, tokenize


def test_tokenizer_recognises_keywords_in_both_languages_case_insensitively() -> None:
    tokens = tokenize("Si vitesse EST rapide and age is not jeune ALORS score EST bon")
    kinds = [t.type for t in tokens]
    assert kinds[0] is TokenType.KEYWORD and tokens[0].value == "IF"
    assert tokens[4].value == "AND" and tokens[6].value == "IS" and tokens[7].value == "NOT"
    assert kinds[-1] is TokenType.EOF


def test_tokenizer_handles_identifiers_with_digits_accents_and_punctuation() -> None:
    tokens = tokenize("RÈGLE T1: (buts_p90 EST élevé)")
    assert [t.value for t in tokens[:-1]] == [
        "RULE",
        "T1",
        ":",
        "(",
        "buts_p90",
        "IS",
        "élevé",
        ")",
    ]


def test_tokenizer_reports_unexpected_characters_with_position() -> None:
    with pytest.raises(ParseError, match="ligne 2, colonne 3"):
        tokenize("ok\n  @")


def test_parse_simple_rule_in_french_and_english() -> None:
    fr = parse_rule("SI vitesse EST rapide ET age EST jeune ALORS score EST excellent", "R1")
    en = parse_rule("IF vitesse IS rapide AND age IS jeune THEN score IS excellent", "R1")
    assert fr == en
    assert fr.antecedent == And(Atom("vitesse", "rapide"), Atom("age", "jeune"))
    assert fr.consequents[0].variable == "score"
    assert fr.render(FRENCH) == "SI vitesse EST rapide ET age EST jeune ALORS score EST excellent"


def test_precedence_not_over_and_over_or() -> None:
    f = parse_formula("a EST x OU NON b EST y ET c EST z")
    assert f == Or(Atom("a", "x"), And(Not(Atom("b", "y")), Atom("c", "z")))
    g = parse_formula("(a EST x OU b EST y) ET c EST z")
    assert g == And(Or(Atom("a", "x"), Atom("b", "y")), Atom("c", "z"))


def test_negated_atoms_in_both_syntaxes_and_double_negation() -> None:
    assert parse_formula("a N'EST PAS x") == Not(Atom("a", "x"))
    assert parse_formula("a IS NOT x") == Not(Atom("a", "x"))
    assert parse_formula("NOT NOT a IS x") == Not(Not(Atom("a", "x")))
    assert parse_formula("a n’est pas x") == Not(Atom("a", "x"))  # apostrophe typographique


def test_modifiers_are_parsed_before_the_term() -> None:
    f = parse_formula("vitesse EST très rapide")
    assert isinstance(f, Atom) and f.modifier is not None and f.modifier.name == "very"
    g = parse_formula("vitesse IS somewhat lente")
    assert isinstance(g, Atom) and g.modifier is not None and g.modifier.name == "somewhat"


def test_rule_prefix_identifier_and_explicit_override() -> None:
    rule = parse_rule("REGLE T7: SI a EST x ALORS s EST y")
    assert rule.identifier == "T7"
    assert parse_rule("RULE 12: IF a IS x THEN s IS y").identifier == "12"
    assert parse_rule("REGLE T7: SI a EST x ALORS s EST y", identifier="Z").identifier == "Z"
    assert parse_rule("SI a EST x ALORS s EST y").identifier == "R"


def test_multiple_consequents_weight_and_description() -> None:
    rule = parse_rule("SI a EST x ALORS s EST y ET t EST z", "R", weight=0.5, description="d")
    assert [c.variable for c in rule.consequents] == ["s", "t"]
    assert rule.weight == 0.5 and rule.description == "d"
    assert str(rule) == "IF a IS x THEN s IS y AND t IS z"


@pytest.mark.parametrize(
    ("text", "fragment"),
    [
        ("SI vitesse rapide ALORS s EST y", "IS/EST attendu"),
        ("SI vitesse EST rapide ALORS", "variable de sortie"),
        ("SI vitesse EST rapide ALORS s EST y extra", "Texte inattendu"),
        ("vitesse EST rapide ALORS s EST y", "IF/SI"),
        ("SI (vitesse EST rapide ALORS s EST y", r"'\)' attendu"),
        ("SI vitesse EST ALORS s EST y", "terme"),
        ("SI vitesse N'EST rapide ALORS s EST y", "PAS"),
    ],
)
def test_parse_errors_are_explicit(text: str, fragment: str) -> None:
    with pytest.raises(ParseError, match=fragment):
        parse_rule(text)
