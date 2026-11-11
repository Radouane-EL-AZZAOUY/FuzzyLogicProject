"""Operator-precedence (Pratt) parser for the Prolog-like language.

Standard Prolog operator table (subset) plus two additions:

* ``Clause @ Degree.`` — a truth degree attached to a fact or rule;
* ``a ~ b @ Degree.`` — a similarity declaration between two constants.

Grammar (informal)::

    program  := { clause }
    clause   := term [ '@' number ] '.'
    query    := term [ '.' ]
    term     := operator-precedence expression over primaries
    primary  := number | string | variable | atom | atom '(' args ')' | list | '(' term ')'
"""

from __future__ import annotations

from collections.abc import Iterator
from dataclasses import dataclass

from fuzzyprolog.exceptions import ParseError
from fuzzyprolog.operators import ARGUMENT_PRIORITY, INFIX, PREFIX, argument_priorities
from fuzzyprolog.parser.lexer import Kind, Token, tokenize
from fuzzyprolog.terms import EMPTY_LIST, Atom, Number, String, Struct, Term, Var, make_list

DEGREE_MARK = "@"


@dataclass(frozen=True, slots=True)
class ParsedItem:
    """A top-level clause as read: the term, its optional degree and its line."""

    term: Term
    degree: float
    line: int


class Parser:
    def __init__(self, tokens: list[Token]) -> None:
        self._tokens = tokens
        self._pos = 0
        self._variables: dict[str, Var] = {}
        self._anonymous = 0

    # --- token helpers -------------------------------------------------------------

    def _peek(self, offset: int = 0) -> Token:
        index = min(self._pos + offset, len(self._tokens) - 1)
        return self._tokens[index]

    def _advance(self) -> Token:
        token = self._peek()
        if token.kind is not Kind.EOF:
            self._pos += 1
        return token

    def _error(self, message: str, token: Token | None = None) -> ParseError:
        token = token or self._peek()
        return ParseError(message, token.line, token.column)

    def _expect_punct(self, text: str) -> None:
        token = self._peek()
        if token.kind is Kind.PUNCT and token.text == text:
            self._advance()
            return
        raise self._error(f"'{text}' attendu, trouvé {token}")

    def _reset_variables(self) -> None:
        self._variables = {}

    # --- entry points -----------------------------------------------------------------

    def read_program(self) -> Iterator[ParsedItem]:
        while self._peek().kind is not Kind.EOF:
            self._reset_variables()
            line = self._peek().line
            term, _ = self.parse(1200)
            degree = self._optional_degree()
            token = self._peek()
            if token.kind is not Kind.END:
                raise self._error(f"'.' attendu en fin de clause, trouvé {token}")
            self._advance()
            yield ParsedItem(term, degree, line)

    def read_query(self) -> Term:
        self._reset_variables()
        if self._peek().kind is Kind.EOF:
            raise self._error("Requête vide")
        term, _ = self.parse(1200)
        if self._peek().kind is Kind.END:
            self._advance()
        if self._peek().kind is not Kind.EOF:
            raise self._error(f"Texte inattendu après la requête : {self._peek()}")
        return term

    def _optional_degree(self) -> float:
        token = self._peek()
        if token.kind is Kind.ATOM and token.text == DEGREE_MARK:
            self._advance()
            number = self._peek()
            if number.kind is not Kind.NUMBER:
                raise self._error(f"Degré numérique attendu après '@', trouvé {number}")
            self._advance()
            return float(number.text)
        return 1.0

    # --- expressions -------------------------------------------------------------------

    def parse(self, max_priority: int) -> tuple[Term, int]:
        left, left_priority = self._parse_primary(max_priority)
        while True:
            token = self._peek()
            name = self._infix_name(token)
            if name is None:
                break
            priority, kind = INFIX[name]
            if priority > max_priority:
                break
            left_max, right_max = argument_priorities(priority, kind)
            if left_priority > left_max:
                break
            self._advance()
            right, _ = self.parse(right_max)
            left = Struct(name, (left, right))
            left_priority = priority
        return left, left_priority

    def _infix_name(self, token: Token) -> str | None:
        if token.kind is Kind.PUNCT and token.text == ",":
            return ","
        if token.kind is Kind.PUNCT and token.text == "|":
            return ";"
        if token.kind is Kind.ATOM and token.text in INFIX and not token.functional:
            return token.text
        return None

    def _can_start_term(self, token: Token) -> bool:
        if token.kind in (Kind.NUMBER, Kind.STRING, Kind.VAR):
            return True
        if token.kind is Kind.PUNCT:
            return token.text in "([{"
        if token.kind is Kind.ATOM:
            return token.functional or token.text not in INFIX or token.text in PREFIX
        return False

    def _parse_primary(self, max_priority: int) -> tuple[Term, int]:
        token = self._advance()
        if token.kind is Kind.NUMBER:
            return _number(token.text), 0
        if token.kind is Kind.STRING:
            return String(token.text), 0
        if token.kind is Kind.VAR:
            return self._variable(token.text), 0
        if token.kind is Kind.PUNCT:
            if token.text == "(":
                inner, _ = self.parse(1200)
                self._expect_punct(")")
                return inner, 0
            if token.text == "[":
                return self._parse_list(), 0
            raise self._error(f"Terme attendu, trouvé {token}", token)
        if token.kind is Kind.ATOM:
            return self._parse_atom_or_compound(token, max_priority)
        raise self._error(f"Terme attendu, trouvé {token}", token)

    def _parse_atom_or_compound(self, token: Token, max_priority: int) -> tuple[Term, int]:
        name = token.text
        if token.functional:
            self._expect_punct("(")
            args = self._parse_arguments()
            return Struct(name, tuple(args)), 0
        if name in PREFIX and self._can_start_term(self._peek()):
            priority, kind = PREFIX[name]
            if priority > max_priority:
                priority = max_priority
            nxt = self._peek()
            if name == "-" and nxt.kind is Kind.NUMBER:
                self._advance()
                value = _number(nxt.text)
                return Number(-value.value), 0
            operand_max = priority if kind == "fy" else priority - 1
            operand, _ = self.parse(operand_max)
            return Struct(name, (operand,)), priority
        return Atom(name), 0

    def _parse_arguments(self) -> list[Term]:
        args: list[Term] = []
        while True:
            arg, _ = self.parse(ARGUMENT_PRIORITY)
            args.append(arg)
            token = self._peek()
            if token.kind is Kind.PUNCT and token.text == ",":
                self._advance()
                continue
            self._expect_punct(")")
            return args

    def _parse_list(self) -> Term:
        token = self._peek()
        if token.kind is Kind.PUNCT and token.text == "]":
            self._advance()
            return EMPTY_LIST
        items: list[Term] = []
        tail: Term = EMPTY_LIST
        while True:
            item, _ = self.parse(ARGUMENT_PRIORITY)
            items.append(item)
            token = self._peek()
            if token.kind is Kind.PUNCT and token.text == ",":
                self._advance()
                continue
            if token.kind is Kind.PUNCT and token.text == "|":
                self._advance()
                tail, _ = self.parse(ARGUMENT_PRIORITY)
            self._expect_punct("]")
            return make_list(items, tail)

    def _variable(self, name: str) -> Var:
        if name == "_":
            self._anonymous += 1
            return Var("_", -self._anonymous)  # negative index: never produced by renaming
        variable = self._variables.get(name)
        if variable is None:
            variable = Var(name)
            self._variables[name] = variable
        return variable


def _number(text: str) -> Number:
    if any(c in text for c in ".eE"):
        return Number(float(text))
    return Number(int(text))


def parse_program_items(text: str) -> list[ParsedItem]:
    return list(Parser(tokenize(text)).read_program())


def parse_query(text: str) -> tuple[Term, ...]:
    """Parse a query such as ``pere(X, ali), masculin(X)`` into a tuple of goals."""
    return flatten_conjunction(Parser(tokenize(text)).read_query())


def parse_term(text: str) -> Term:
    """Parse a single term (no trailing dot required)."""
    return Parser(tokenize(text)).read_query()


def flatten_conjunction(term: Term) -> tuple[Term, ...]:
    if isinstance(term, Struct) and term.functor == "," and term.arity == 2:
        return flatten_conjunction(term.args[0]) + flatten_conjunction(term.args[1])
    return (term,)
