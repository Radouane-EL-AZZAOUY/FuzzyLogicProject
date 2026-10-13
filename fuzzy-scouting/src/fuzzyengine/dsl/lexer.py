"""Lexer of the rule language.

Token classes: identifiers (variable and term names, Unicode letters allowed),
numbers, keywords (case-insensitive, English or French) and punctuation.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

from fuzzyengine.dsl.syntax import KEYWORD_ALIASES
from fuzzyengine.exceptions import ParseError


class TokenType(Enum):
    IDENT = "identifiant"
    NUMBER = "nombre"
    KEYWORD = "mot-clé"
    LPAREN = "("
    RPAREN = ")"
    COLON = ":"
    EOF = "fin de texte"


@dataclass(frozen=True, slots=True)
class Token:
    type: TokenType
    value: str
    line: int
    column: int

    def is_keyword(self, name: str) -> bool:
        return self.type is TokenType.KEYWORD and self.value == name

    def __str__(self) -> str:
        label = str(self.type.value)
        return label if self.type is TokenType.EOF else f"{label} '{self.value}'"


_PUNCTUATION = {"(": TokenType.LPAREN, ")": TokenType.RPAREN, ":": TokenType.COLON}
_WORD_EXTRA = {"_", "'", "’", "-"}


def _is_word_start(ch: str) -> bool:
    return ch.isalpha() or ch == "_"


def _is_word_char(ch: str) -> bool:
    return ch.isalnum() or ch in _WORD_EXTRA


def tokenize(text: str) -> list[Token]:
    tokens: list[Token] = []
    line, column = 1, 1
    index = 0
    length = len(text)
    while index < length:
        ch = text[index]
        if ch == "\n":
            line, column = line + 1, 1
            index += 1
            continue
        if ch.isspace():
            index += 1
            column += 1
            continue
        start_column = column
        if ch in _PUNCTUATION:
            tokens.append(Token(_PUNCTUATION[ch], ch, line, start_column))
            index += 1
            column += 1
            continue
        if ch.isdigit():
            end = index
            while end < length and (text[end].isdigit() or text[end] == "."):
                end += 1
            tokens.append(Token(TokenType.NUMBER, text[index:end], line, start_column))
            column += end - index
            index = end
            continue
        if _is_word_start(ch):
            end = index
            while end < length and _is_word_char(text[end]):
                end += 1
            word = text[index:end]
            keyword = KEYWORD_ALIASES.get(word.lower().replace("’", "'"))
            if keyword is not None:
                tokens.append(Token(TokenType.KEYWORD, keyword, line, start_column))
            else:
                tokens.append(Token(TokenType.IDENT, word, line, start_column))
            column += end - index
            index = end
            continue
        raise ParseError(f"Caractère inattendu '{ch}'", line, column)
    tokens.append(Token(TokenType.EOF, "", line, column))
    return tokens
