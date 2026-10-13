"""Defuzzification: from an aggregated fuzzy conclusion to a crisp number.

All strategies sample the universe on a regular grid; the resolution trades
accuracy for speed. New strategies implement :class:`Defuzzifier` and register
themselves in :data:`DEFUZZIFIERS`.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import Callable
from dataclasses import dataclass
from typing import ClassVar

from fuzzyengine.exceptions import DefinitionError
from fuzzyengine.universe import Universe

Membership = Callable[[float], float]


class Defuzzifier(ABC):
    name: ClassVar[str] = "abstract"

    @abstractmethod
    def defuzzify(self, membership: Membership, universe: Universe) -> float | None:
        """Crisp representative of ``membership`` over ``universe``.

        Returns ``None`` when the sampled membership is identically zero (no rule
        fired, or the output set is narrower than the sampling grid); the caller
        decides how to report that.
        """


def _sample(
    membership: Membership, universe: Universe, resolution: int
) -> tuple[list[float], list[float]]:
    xs = universe.grid(resolution)
    return xs, [membership(x) for x in xs]


@dataclass(frozen=True, slots=True)
class Centroid(Defuzzifier):
    """Centre of gravity ``Σ x·μ(x) / Σ μ(x)`` (the most common choice)."""

    resolution: int = 501
    name: ClassVar[str] = "centroid"

    def defuzzify(self, membership: Membership, universe: Universe) -> float | None:
        xs, mus = _sample(membership, universe, self.resolution)
        total = sum(mus)
        if total <= 0.0:
            return None
        return sum(x * mu for x, mu in zip(xs, mus, strict=True)) / total


@dataclass(frozen=True, slots=True)
class Bisector(Defuzzifier):
    """Abscissa splitting the area under μ in two equal halves."""

    resolution: int = 501
    name: ClassVar[str] = "bisector"

    def defuzzify(self, membership: Membership, universe: Universe) -> float | None:
        xs, mus = _sample(membership, universe, self.resolution)
        total = sum(mus)
        if total <= 0.0:
            return None
        running = 0.0
        for x, mu in zip(xs, mus, strict=True):
            running += mu
            if running >= total / 2.0:
                return x
        return xs[-1]


@dataclass(frozen=True, slots=True)
class MeanOfMaximum(Defuzzifier):
    """Mean of the abscissas where μ reaches its maximum."""

    resolution: int = 501
    name: ClassVar[str] = "mom"

    def defuzzify(self, membership: Membership, universe: Universe) -> float | None:
        xs, mus = _sample(membership, universe, self.resolution)
        peak = max(mus)
        if peak <= 0.0:
            return None
        maxima = [x for x, mu in zip(xs, mus, strict=True) if abs(mu - peak) < 1e-12]
        return sum(maxima) / len(maxima)


DEFUZZIFIERS: dict[str, type[Defuzzifier]] = {
    Centroid.name: Centroid,
    Bisector.name: Bisector,
    MeanOfMaximum.name: MeanOfMaximum,
}


def defuzzifier_from_name(name: str, resolution: int | None = None) -> Defuzzifier:
    try:
        cls = DEFUZZIFIERS[name.lower()]
    except KeyError as exc:
        raise DefinitionError(
            f"Méthode de défuzzification inconnue : '{name}'. "
            f"Connues : {', '.join(sorted(DEFUZZIFIERS))}."
        ) from exc
    if resolution is None:
        return cls()
    if resolution < 2:
        raise DefinitionError("La résolution de défuzzification doit être >= 2.")
    return cls(resolution=resolution)  # type: ignore[call-arg]
