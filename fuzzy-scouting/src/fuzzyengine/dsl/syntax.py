"""Concrete syntaxes of the rule language (English and French keywords).

This module is the single source of truth for keywords: the lexer uses
:data:`KEYWORD_ALIASES` to recognise them and the renderers use a :class:`Syntax`
to print formulas back in either language.
"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True, slots=True)
class Syntax:
    """Keywords used to render formulas and rules in one natural language."""

    IF: str
    THEN: str
    AND: str
    OR: str
    NOT: str
    IS: str
    IS_NOT: str
    RULE: str
    modifiers: dict[str, str] = field(default_factory=dict)
    """Canonical modifier name → word in this language."""

    def modifier(self, canonical: str) -> str:
        return self.modifiers.get(canonical, canonical)


ENGLISH = Syntax(
    IF="IF",
    THEN="THEN",
    AND="AND",
    OR="OR",
    NOT="NOT",
    IS="IS",
    IS_NOT="IS NOT",
    RULE="RULE",
    modifiers={"very": "very", "somewhat": "somewhat", "extremely": "extremely"},
)

FRENCH = Syntax(
    IF="SI",
    THEN="ALORS",
    AND="ET",
    OR="OU",
    NOT="NON",
    IS="EST",
    IS_NOT="N'EST PAS",
    RULE="RÈGLE",
    modifiers={"very": "très", "somewhat": "assez", "extremely": "extrêmement"},
)

SYNTAXES: dict[str, Syntax] = {"en": ENGLISH, "fr": FRENCH}

KEYWORD_ALIASES: dict[str, str] = {
    # English
    "if": "IF",
    "then": "THEN",
    "and": "AND",
    "or": "OR",
    "not": "NOT",
    "is": "IS",
    "rule": "RULE",
    # French
    "si": "IF",
    "alors": "THEN",
    "et": "AND",
    "ou": "OR",
    "non": "NOT",
    "est": "IS",
    "n'est": "IS_NOT",
    "pas": "PAS",
    "regle": "RULE",
    "règle": "RULE",
}
"""Lower-cased word → canonical keyword token value (case-insensitive matching)."""
