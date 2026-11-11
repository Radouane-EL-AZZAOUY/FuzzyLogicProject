"""Lexer and parser of the fuzzy Prolog language."""

from fuzzyprolog.parser.lexer import Kind, Token, tokenize
from fuzzyprolog.parser.parser import (
    ParsedItem,
    flatten_conjunction,
    parse_program_items,
    parse_query,
    parse_term,
)

__all__ = [
    "Kind",
    "ParsedItem",
    "Token",
    "flatten_conjunction",
    "parse_program_items",
    "parse_query",
    "parse_term",
    "tokenize",
]
