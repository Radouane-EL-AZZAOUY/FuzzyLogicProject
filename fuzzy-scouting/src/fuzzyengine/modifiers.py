"""Linguistic hedges (modifiers) such as *very* / *somewhat*.

A hedge transforms a membership degree; it lets rules say ``vitesse EST très rapide``
without defining a new term (Zadeh's concentration and dilation operators).
"""

from __future__ import annotations

import math
from typing import Protocol, runtime_checkable

from fuzzyengine.exceptions import DefinitionError


@runtime_checkable
class Modifier(Protocol):
    name: str

    def __call__(self, degree: float) -> float: ...


class Very:
    """Concentration ``μ²`` (makes the predicate more demanding)."""

    name = "very"

    def __call__(self, degree: float) -> float:
        return degree * degree


class Somewhat:
    """Dilation ``√μ`` (makes the predicate more lenient)."""

    name = "somewhat"

    def __call__(self, degree: float) -> float:
        return math.sqrt(degree)


class Extremely:
    """Strong concentration ``μ³``."""

    name = "extremely"

    def __call__(self, degree: float) -> float:
        return degree * degree * degree


MODIFIERS: dict[str, Modifier] = {m.name: m for m in (Very(), Somewhat(), Extremely())}

MODIFIER_ALIASES: dict[str, str] = {
    # English
    "very": "very",
    "somewhat": "somewhat",
    "extremely": "extremely",
    # French
    "tres": "very",
    "très": "very",
    "assez": "somewhat",
    "plutot": "somewhat",
    "plutôt": "somewhat",
    "extremement": "extremely",
    "extrêmement": "extremely",
}


def is_modifier_name(word: str) -> bool:
    return word.lower() in MODIFIER_ALIASES


def modifier_from_name(name: str) -> Modifier:
    canonical = MODIFIER_ALIASES.get(name.lower())
    if canonical is None:
        raise DefinitionError(
            f"Modificateur linguistique inconnu : '{name}'. "
            f"Connus : {', '.join(sorted(MODIFIER_ALIASES))}."
        )
    return MODIFIERS[canonical]
