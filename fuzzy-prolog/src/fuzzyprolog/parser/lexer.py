"""Tokeniser of the Prolog-like language.

Token classes: names (atoms), variables, numbers, double-quoted strings, symbolic
atoms (``:-``, ``=..``, ``@``, ``~`` …), punctuation and the clause terminator ``.``
(a dot followed by a blank, a comment or the end of text).
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

from fuzzyprolog.exceptions import ParseError


class Kind(Enum):
    ATOM = "atome"
    VAR = "variable"
    NUMBER = "nombre"
    STRING = "chaîne"
    PUNCT = "ponctuation"
    END = "fin de clause"
    EOF = "fin de texte"


@dataclass(frozen=True, slots=True)
class Token:
    kind: Kind
    text: str
    line: int
    column: int
    functional: bool = False
    """``True`` when an atom is immediately followed by ``(`` (functional notation)."""

    def __str__(self) -> str:
        if self.kind in (Kind.END, Kind.EOF):
            return str(self.kind.value)
        return f"{self.kind.value} '{self.text}'"


SYMBOL_CHARS = set("+-*/\\^<>=~:.?@#&$")
SOLO_ATOMS = {"!", ";"}
PUNCTUATION = set("()[]{},|")
_ESCAPES = {"n": "\n", "t": "\t", "\\": "\\", "'": "'", '"': '"'}


class Lexer:
    def __init__(self, text: str) -> None:
        self._text = text
        self._pos = 0
        self._line = 1
        self._col = 1

    # --- helpers ----------------------------------------------------------------

    def _peek(self, offset: int = 0) -> str:
        index = self._pos + offset
        return self._text[index] if index < len(self._text) else ""

    def _advance(self) -> str:
        ch = self._text[self._pos]
        self._pos += 1
        if ch == "\n":
            self._line += 1
            self._col = 1
        else:
            self._col += 1
        return ch

    def _error(self, message: str) -> ParseError:
        return ParseError(message, self._line, self._col)

    def _skip_blanks_and_comments(self) -> None:
        while self._pos < len(self._text):
            ch = self._peek()
            if ch.isspace():
                self._advance()
            elif ch == "%":
                while self._pos < len(self._text) and self._peek() != "\n":
                    self._advance()
            elif ch == "/" and self._peek(1) == "*":
                self._advance()
                self._advance()
                while self._pos < len(self._text) and not (
                    self._peek() == "*" and self._peek(1) == "/"
                ):
                    self._advance()
                if self._pos >= len(self._text):
                    raise self._error("Commentaire /* non terminé")
                self._advance()
                self._advance()
            else:
                return

    def _read_quoted(self, quote: str) -> str:
        self._advance()  # opening quote
        chars: list[str] = []
        while True:
            if self._pos >= len(self._text):
                raise self._error(f"Texte entre {quote} non terminé")
            ch = self._advance()
            if ch == quote:
                if self._peek() == quote:  # doubled quote
                    self._advance()
                    chars.append(quote)
                    continue
                return "".join(chars)
            if ch == "\\":
                escaped = self._advance() if self._pos < len(self._text) else ""
                chars.append(_ESCAPES.get(escaped, escaped))
                continue
            chars.append(ch)

    # --- main loop ----------------------------------------------------------------

    def tokens(self) -> list[Token]:
        tokens: list[Token] = []
        while True:
            self._skip_blanks_and_comments()
            if self._pos >= len(self._text):
                tokens.append(Token(Kind.EOF, "", self._line, self._col))
                return tokens
            line, col = self._line, self._col
            ch = self._peek()
            if ch.isdigit():
                tokens.append(Token(Kind.NUMBER, self._read_number(), line, col))
            elif ch == '"':
                tokens.append(Token(Kind.STRING, self._read_quoted('"'), line, col))
            elif ch == "'":
                name = self._read_quoted("'")
                tokens.append(Token(Kind.ATOM, name, line, col, self._peek() == "("))
            elif ch.isalpha() or ch == "_":
                word = self._read_word()
                if word[0].isupper() or word[0] == "_":
                    tokens.append(Token(Kind.VAR, word, line, col))
                else:
                    tokens.append(Token(Kind.ATOM, word, line, col, self._peek() == "("))
            elif ch in SOLO_ATOMS:
                self._advance()
                tokens.append(Token(Kind.ATOM, ch, line, col, self._peek() == "("))
            elif ch in PUNCTUATION:
                self._advance()
                tokens.append(Token(Kind.PUNCT, ch, line, col))
            elif ch == "." and self._is_end_dot():
                self._advance()
                tokens.append(Token(Kind.END, ".", line, col))
            elif ch in SYMBOL_CHARS:
                symbol = self._read_symbol()
                tokens.append(Token(Kind.ATOM, symbol, line, col, self._peek() == "("))
            else:
                raise self._error(f"Caractère inattendu '{ch}'")

    def _is_end_dot(self) -> bool:
        nxt = self._peek(1)
        return nxt == "" or nxt.isspace() or nxt == "%"

    def _read_word(self) -> str:
        start = self._pos
        while self._pos < len(self._text) and (self._peek().isalnum() or self._peek() == "_"):
            self._advance()
        return self._text[start : self._pos]

    def _read_symbol(self) -> str:
        start = self._pos
        while self._pos < len(self._text) and self._peek() in SYMBOL_CHARS:
            self._advance()
        return self._text[start : self._pos]

    def _read_number(self) -> str:
        start = self._pos
        while self._peek().isdigit():
            self._advance()
        if self._peek() == "." and self._peek(1).isdigit():
            self._advance()
            while self._peek().isdigit():
                self._advance()
        if self._peek() in ("e", "E") and (
            self._peek(1).isdigit() or (self._peek(1) in "+-" and self._peek(2).isdigit())
        ):
            self._advance()
            if self._peek() in "+-":
                self._advance()
            while self._peek().isdigit():
                self._advance()
        return self._text[start : self._pos]


def tokenize(text: str) -> list[Token]:
    return Lexer(text).tokens()
