"""Fuzzification: from observations to an :class:`Interpretation`.

This is the step where the course's *interprétation* ``δ : P → {□, ■}`` becomes
``δ : P → [0, 1]``: each observed value is projected on every term of its variable.
An observation is a precise number, an interval, a category or explicit degrees
(see :mod:`fuzzyengine.observations`).
"""

from __future__ import annotations

import math
from collections.abc import Mapping
from dataclasses import dataclass

from fuzzyengine.exceptions import EvaluationError
from fuzzyengine.formulas import Interpretation
from fuzzyengine.observations import Category, Degrees, Interval, Observation
from fuzzyengine.variables import FuzzySet, LinguisticVariable

INTERVAL_SAMPLES = 101
"""Regular samples taken inside an interval, on top of its bounds and of the shape
parameters (which are the breakpoints of piecewise-linear shapes, so the supremum of
triangles, trapezoids and ramps is exact)."""


@dataclass(frozen=True, slots=True)
class FuzzificationResult:
    interpretation: Interpretation
    values: dict[str, float]
    """Precise values actually used (after clamping); imprecise inputs are absent."""
    warnings: tuple[str, ...]
    observations: dict[str, Observation]
    """Every input as it was used: number, interval, category or degrees."""


def _as_finite_float(name: str, raw: object) -> float:
    try:
        value = float(raw)  # type: ignore[arg-type]
    except (TypeError, ValueError) as exc:
        raise EvaluationError(f"La valeur de '{name}' n'est pas numérique : {raw!r}.") from exc
    if not math.isfinite(value):
        raise EvaluationError(f"La valeur de '{name}' est NaN ou infinie ({value}).")
    return value


def _possibility(term: FuzzySet, lower: float, upper: float) -> float:
    """``sup { μ(x) : x ∈ [lower, upper] }``."""
    points = {lower, upper}
    points.update(p for p in term.membership.parameters() if lower <= p <= upper)
    if upper > lower:
        step = (upper - lower) / (INTERVAL_SAMPLES - 1)
        points.update(lower + i * step for i in range(1, INTERVAL_SAMPLES - 1))
    return max(term.degree(x) for x in points)


class Fuzzifier:
    """Fuzzifies a set of observations against declared variables."""

    def __init__(self, variables: Mapping[str, LinguisticVariable]) -> None:
        self._variables = dict(variables)

    def fuzzify(self, values: Mapping[str, Observation]) -> FuzzificationResult:
        missing = [name for name in self._variables if name not in values]
        if missing:
            raise EvaluationError(f"Valeur(s) d'entrée manquante(s) : {', '.join(missing)}.")
        degrees: dict[str, dict[str, float]] = {}
        used: dict[str, float] = {}
        observations: dict[str, Observation] = {}
        warnings: list[str] = []
        for name, variable in self._variables.items():
            observation = values[name]
            if isinstance(observation, Interval):
                observations[name], degrees[name] = self._interval(variable, observation, warnings)
            elif isinstance(observation, Category):
                observations[name], degrees[name] = self._category(variable, observation)
            elif isinstance(observation, Degrees):
                observations[name], degrees[name] = self._degrees(variable, observation)
            else:
                raw = _as_finite_float(name, observation)
                value = variable.universe.clamp(raw)
                if value != raw:
                    warnings.append(self._out_of_universe(variable, f"{raw:g}", f"{value:g}"))
                used[name] = value
                observations[name] = value
                degrees[name] = variable.fuzzify(value)
        return FuzzificationResult(Interpretation(degrees), used, tuple(warnings), observations)

    @staticmethod
    def _out_of_universe(variable: LinguisticVariable, given: str, kept: str) -> str:
        universe = variable.universe
        return (
            f"'{variable.name}' = {given} hors de l'univers "
            f"[{universe.lower:g}, {universe.upper:g}] : ramené à {kept}."
        )

    def _interval(
        self, variable: LinguisticVariable, interval: Interval, warnings: list[str]
    ) -> tuple[Interval, dict[str, float]]:
        universe = variable.universe
        clamped = Interval(universe.clamp(interval.lower), universe.clamp(interval.upper))
        if clamped != interval:
            warnings.append(self._out_of_universe(variable, str(interval), str(clamped)))
        return clamped, {
            term.label: _possibility(term, clamped.lower, clamped.upper) for term in variable.terms
        }

    @staticmethod
    def _category(
        variable: LinguisticVariable, category: Category
    ) -> tuple[Category, dict[str, float]]:
        if not variable.has_term(category.term):
            raise EvaluationError(
                f"Catégorie inconnue '{category.term}' pour '{variable.name}' "
                f"(catégories possibles : {', '.join(variable.labels)})."
            )
        return category, {
            label: 1.0 if label == category.term else 0.0 for label in variable.labels
        }

    @staticmethod
    def _degrees(variable: LinguisticVariable, given: Degrees) -> tuple[Degrees, dict[str, float]]:
        unknown = [term for term in given.degrees if not variable.has_term(term)]
        if unknown:
            raise EvaluationError(
                f"Terme(s) inconnu(s) pour '{variable.name}' : {', '.join(unknown)} "
                f"(termes possibles : {', '.join(variable.labels)})."
            )
        return given, {label: given.degrees.get(label, 0.0) for label in variable.labels}
