"""Fuzzification: from crisp measurements to an :class:`Interpretation`.

This is the step where the course's *interprétation* ``δ : P → {□, ■}`` becomes
``δ : P → [0, 1]``: each measured value is projected on every term of its variable.
"""

from __future__ import annotations

import math
from collections.abc import Mapping
from dataclasses import dataclass

from fuzzyengine.exceptions import EvaluationError
from fuzzyengine.formulas import Interpretation
from fuzzyengine.variables import LinguisticVariable


@dataclass(frozen=True, slots=True)
class FuzzificationResult:
    interpretation: Interpretation
    values: dict[str, float]
    """Values actually used (after clamping to the universe)."""
    warnings: tuple[str, ...]


def _as_finite_float(name: str, raw: object) -> float:
    try:
        value = float(raw)  # type: ignore[arg-type]
    except (TypeError, ValueError) as exc:
        raise EvaluationError(f"La valeur de '{name}' n'est pas numérique : {raw!r}.") from exc
    if not math.isfinite(value):
        raise EvaluationError(f"La valeur de '{name}' est NaN ou infinie ({value}).")
    return value


class Fuzzifier:
    """Fuzzifies a set of crisp input values against declared variables."""

    def __init__(self, variables: Mapping[str, LinguisticVariable]) -> None:
        self._variables = dict(variables)

    def fuzzify(self, values: Mapping[str, float]) -> FuzzificationResult:
        missing = [name for name in self._variables if name not in values]
        if missing:
            raise EvaluationError(f"Valeur(s) d'entrée manquante(s) : {', '.join(missing)}.")
        degrees: dict[str, dict[str, float]] = {}
        used: dict[str, float] = {}
        warnings: list[str] = []
        for name, variable in self._variables.items():
            raw = _as_finite_float(name, values[name])
            value = variable.universe.clamp(raw)
            if value != raw:
                warnings.append(
                    f"'{name}' = {raw:g} hors de l'univers "
                    f"[{variable.universe.lower:g}, {variable.universe.upper:g}] : "
                    f"ramené à {value:g}."
                )
            used[name] = value
            degrees[name] = variable.fuzzify(value)
        return FuzzificationResult(Interpretation(degrees), used, tuple(warnings))
