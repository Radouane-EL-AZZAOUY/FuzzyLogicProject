"""Recursive-descent parser of the rule language.

Grammar (EBNF, keywords case-insensitive, English or French)::

    rule        := [ RULE ident ":" ] IF formula THEN consequent { AND consequent }
    formula     := disjunction
    disjunction := conjunction { OR conjunction }
    conjunction := negation { AND negation }
    negation    := NOT negation | primary
    primary     := "(" formula ")" | atom
    atom        := ident ( IS [ NOT ] | IS_NOT PAS ) [ modifier ] ident
    consequent  := ident IS ident

Precedence ``NOT > AND > OR`` follows the course's parenthesis-elimination rules.
"""

from __future__ import annotations

from fuzzyengine.dsl.lexer import Token, TokenType, tokenize
from fuzzyengine.exceptions import ParseError
from fuzzyengine.formulas import And, Atom, Formula, Not, Or
from fuzzyengine.modifiers import is_modifier_name, modifier_from_name
from fuzzyengine.rules import Consequent, Rule


class _Parser:
    def __init__(self, tokens: list[Token]) -> None:
        self._tokens = tokens
        self._position = 0

    # --- token helpers -------------------------------------------------------

    def _peek(self, offset: int = 0) -> Token:
        index = min(self._position + offset, len(self._tokens) - 1)
        return self._tokens[index]

    def _advance(self) -> Token:
        token = self._peek()
        if token.type is not TokenType.EOF:
            self._position += 1
        return token

    def _match_keyword(self, name: str) -> bool:
        if self._peek().is_keyword(name):
            self._advance()
            return True
        return False

    def _expect_keyword(self, name: str, hint: str) -> Token:
        token = self._peek()
        if not token.is_keyword(name):
            raise ParseError(f"{hint} attendu, trouvé {token}", token.line, token.column)
        return self._advance()

    def _expect(self, token_type: TokenType, hint: str) -> Token:
        token = self._peek()
        if token.type is not token_type:
            raise ParseError(f"{hint} attendu, trouvé {token}", token.line, token.column)
        return self._advance()

    def _expect_name(self, hint: str) -> str:
        token = self._peek()
        if token.type in (TokenType.IDENT, TokenType.NUMBER):
            return self._advance().value
        raise ParseError(f"{hint} attendu, trouvé {token}", token.line, token.column)

    # --- grammar -------------------------------------------------------------

    def parse_rule(self, identifier: str | None, weight: float, description: str) -> Rule:
        prefix_identifier: str | None = None
        if self._match_keyword("RULE"):
            prefix_identifier = self._expect_name("Identifiant de règle")
            self._expect(TokenType.COLON, "':'")
        self._expect_keyword("IF", "Mot-clé IF/SI")
        antecedent = self.parse_formula()
        self._expect_keyword("THEN", "Mot-clé THEN/ALORS")
        consequents = [self._parse_consequent()]
        while self._match_keyword("AND"):
            consequents.append(self._parse_consequent())
        self._expect_eof()
        return Rule(
            identifier=identifier or prefix_identifier or "R",
            antecedent=antecedent,
            consequents=tuple(consequents),
            weight=weight,
            description=description,
        )

    def parse_formula(self) -> Formula:
        left = self._parse_conjunction()
        while self._match_keyword("OR"):
            left = Or(left, self._parse_conjunction())
        return left

    def _parse_conjunction(self) -> Formula:
        left = self._parse_negation()
        while self._match_keyword("AND"):
            left = And(left, self._parse_negation())
        return left

    def _parse_negation(self) -> Formula:
        if self._match_keyword("NOT"):
            return Not(self._parse_negation())
        return self._parse_primary()

    def _parse_primary(self) -> Formula:
        if self._peek().type is TokenType.LPAREN:
            self._advance()
            inner = self.parse_formula()
            self._expect(TokenType.RPAREN, "')'")
            return inner
        return self._parse_atom()

    def _parse_atom(self) -> Formula:
        variable = self._expect(TokenType.IDENT, "Nom de variable").value
        negated = False
        if self._match_keyword("IS"):
            negated = self._match_keyword("NOT")
        elif self._match_keyword("IS_NOT"):
            self._expect_keyword("PAS", "Mot-clé PAS")
            negated = True
        else:
            token = self._peek()
            raise ParseError(
                f"Mot-clé IS/EST attendu après '{variable}', trouvé {token}",
                token.line,
                token.column,
            )
        modifier = None
        candidate = self._peek()
        if (
            candidate.type is TokenType.IDENT
            and is_modifier_name(candidate.value)
            and self._peek(1).type is TokenType.IDENT
        ):
            modifier = modifier_from_name(self._advance().value)
        term = self._expect(TokenType.IDENT, "Nom de terme").value
        atom = Atom(variable, term, modifier)
        return Not(atom) if negated else atom

    def _parse_consequent(self) -> Consequent:
        variable = self._expect(TokenType.IDENT, "Nom de variable de sortie").value
        self._expect_keyword("IS", "Mot-clé IS/EST")
        term = self._expect(TokenType.IDENT, "Nom de terme de sortie").value
        return Consequent(variable, term)

    def _expect_eof(self) -> None:
        token = self._peek()
        if token.type is not TokenType.EOF:
            raise ParseError(f"Texte inattendu après la règle : {token}", token.line, token.column)


def parse_formula(text: str) -> Formula:
    """Parse a bare formula such as ``vitesse EST rapide ET age EST jeune``."""
    parser = _Parser(tokenize(text))
    formula = parser.parse_formula()
    parser._expect_eof()
    return formula


def parse_rule(
    text: str,
    identifier: str | None = None,
    weight: float = 1.0,
    description: str = "",
) -> Rule:
    """Parse one rule. ``identifier`` overrides an optional ``RULE id:`` prefix."""
    return _Parser(tokenize(text)).parse_rule(identifier, weight, description)
