"""Observations: what is known about an input, precise or not.

A measurement is not always a number. A scout may know a sprint time exactly
(``4.12``), only within a range (``[4.0 ; 4.3]``) or only as a judgement
(``court``). The engine accepts the three forms, plus explicit degrees:

* a ``float``            — precise value (classical *singleton* fuzzification);
* an :class:`Interval`   — the value lies somewhere in ``[lower, upper]``;
* a :class:`Category`    — a linguistic term of the variable, taken as fully true;
* a :class:`Degrees`     — the truth degree of every term, given directly (this is
  how a fuzzy conclusion is handed to the next stage of a pipeline without being
  defuzzified in between).

Fuzzification of an interval follows possibility theory: the degree of a term is
the best membership reachable inside the interval, ``Π(T) = sup { μ_T(x) : x ∈ [a, b] }``.
A precise value is the special case ``a = b``.
"""

from __future__ import annotations

import math
import re
from collections.abc import Mapping
from dataclasses import dataclass, field
from types import MappingProxyType

from fuzzyengine.exceptions import EvaluationError


@dataclass(frozen=True, slots=True)
class Interval:
    """The value is only known to lie in ``[lower, upper]``."""

    lower: float
    upper: float

    def __post_init__(self) -> None:
        if not (math.isfinite(self.lower) and math.isfinite(self.upper)):
            raise EvaluationError(
                f"Intervalle invalide [{self.lower} ; {self.upper}] : bornes NaN ou infinies."
            )
        if self.lower > self.upper:
            raise EvaluationError(
                f"Intervalle invalide [{self.lower:g} ; {self.upper:g}] : "
                "la borne inférieure dépasse la borne supérieure."
            )

    @property
    def midpoint(self) -> float:
        return (self.lower + self.upper) / 2.0

    def __str__(self) -> str:
        return f"[{self.lower:g} ; {self.upper:g}]"


@dataclass(frozen=True, slots=True)
class Category:
    """The value is only known as a linguistic term of its variable (e.g. ``moyenne``)."""

    term: str

    def __post_init__(self) -> None:
        if not self.term.strip():
            raise EvaluationError("Une catégorie ne peut pas être vide.")

    def __str__(self) -> str:
        return self.term


@dataclass(frozen=True, slots=True)
class Degrees:
    """Truth degree of each term, given directly (terms left out count as 0)."""

    degrees: Mapping[str, float] = field(default_factory=dict)

    def __post_init__(self) -> None:
        clean: dict[str, float] = {}
        for term, raw in self.degrees.items():
            try:
                degree = float(raw)
            except (TypeError, ValueError) as exc:
                raise EvaluationError(f"Degré non numérique pour '{term}' : {raw!r}.") from exc
            if not 0.0 <= degree <= 1.0:  # also rejects NaN
                raise EvaluationError(f"Degré hors de [0, 1] pour '{term}' : {raw!r}.")
            clean[term] = degree
        object.__setattr__(self, "degrees", MappingProxyType(clean))

    def __str__(self) -> str:
        return "{" + ", ".join(f"{t}={d:.2f}" for t, d in self.degrees.items()) + "}"


Observation = float | Interval | Category | Degrees
"""Anything the fuzzifier accepts as the value of an input."""

_NUMBER = r"[-+]?(?:\d+(?:[.,]\d*)?|[.,]\d+)(?:[eE][-+]?\d+)?"
_INTERVAL_PATTERNS = (
    re.compile(rf"^\[\s*({_NUMBER})\s*;\s*({_NUMBER})\s*\]$"),
    re.compile(rf"^({_NUMBER})\s*\.\.\s*({_NUMBER})$"),
)
_NUMBER_PATTERN = re.compile(rf"^{_NUMBER}$")
_NON_FINITE = {"nan", "inf", "+inf", "-inf", "infinity", "+infinity", "-infinity"}


def _number(text: str) -> float:
    value = float(text.replace(",", "."))
    if not math.isfinite(value):
        raise EvaluationError(f"Valeur non finie : '{text}'.")
    return value


def parse_observation(raw: object) -> Observation:
    """Read an observation from loosely typed data (CSV cell, JSON value, CLI argument).

    Accepted forms: a number (``34.5``, ``"34,5"``), an interval (``"30..33"``,
    ``"[30 ; 33]"``, a pair ``[30, 33]``, ``{"min": 30, "max": 33}``), a category
    (``"moyenne"``) or explicit degrees (``{"fort": 0.7, "moyenne": 0.3}``).

    >>> parse_observation("4,0..4,3")
    Interval(lower=4.0, upper=4.3)
    >>> parse_observation("rapide")
    Category(term='rapide')
    """
    if isinstance(raw, Interval | Category | Degrees):
        return raw
    if isinstance(raw, bool):
        raise EvaluationError(f"Observation invalide : {raw!r}.")
    if isinstance(raw, int | float):
        if not math.isfinite(raw):
            raise EvaluationError(f"Valeur non finie : {raw!r}.")
        return float(raw)
    if isinstance(raw, list | tuple):
        if len(raw) != 2 or not all(
            isinstance(b, int | float) and not isinstance(b, bool) for b in raw
        ):
            raise EvaluationError(
                f"Un intervalle s'écrit [min, max] avec deux nombres (reçu {raw!r})."
            )
        return Interval(float(raw[0]), float(raw[1]))
    if isinstance(raw, Mapping):
        if set(raw) == {"min", "max"}:
            return parse_observation([raw["min"], raw["max"]])
        return Degrees({str(term): degree for term, degree in raw.items()})
    if isinstance(raw, str):
        text = raw.strip()
        if not text:
            raise EvaluationError("Observation vide.")
        if text.lower() in _NON_FINITE:
            raise EvaluationError(f"Valeur non finie : '{text}'.")
        if _NUMBER_PATTERN.match(text):
            return _number(text)
        for pattern in _INTERVAL_PATTERNS:
            match = pattern.match(text)
            if match:
                return Interval(_number(match.group(1)), _number(match.group(2)))
        if text[0].isalpha() or text[0] == "_":
            return Category(text)
        raise EvaluationError(
            f"Observation illisible : '{raw}' (attendu : un nombre, un intervalle "
            "« min..max » ou une catégorie)."
        )
    raise EvaluationError(f"Observation invalide : {raw!r}.")
