"""Membership functions μ : ℝ → [0, 1].

A membership function generalises the characteristic function of a classical set
(which only takes the values 0 and 1, i.e. the ``{□, ■}`` truth values of the course).
Every function here is an immutable *strategy* object; new shapes can be added by
subclassing :class:`MembershipFunction` and registering the class in
:data:`MEMBERSHIP_REGISTRY` (open/closed principle).
"""

from __future__ import annotations

import math
from abc import ABC, abstractmethod
from collections.abc import Sequence
from dataclasses import dataclass
from itertools import pairwise
from typing import ClassVar

from fuzzyengine.exceptions import DefinitionError


class MembershipFunction(ABC):
    """Abstract membership function (callable strategy)."""

    kind: ClassVar[str] = "abstract"

    @abstractmethod
    def __call__(self, x: float) -> float:
        """Degree of membership of ``x``, always within ``[0, 1]``."""

    @abstractmethod
    def parameters(self) -> tuple[float, ...]:
        """Shape parameters, in the order expected by :func:`membership_from_spec`."""

    def __str__(self) -> str:
        params = ", ".join(f"{p:g}" for p in self.parameters())
        return f"{self.kind}({params})"


def _require_sorted(name: str, values: Sequence[float]) -> None:
    if any(b < a for a, b in pairwise(values)):
        raise DefinitionError(
            f"Paramètres de '{name}' invalides {tuple(values)} : ils doivent être croissants."
        )


@dataclass(frozen=True, slots=True)
class Triangular(MembershipFunction):
    """Triangle with feet ``a`` and ``c`` and peak ``b`` (``a <= b <= c``, ``a < c``)."""

    a: float
    b: float
    c: float
    kind: ClassVar[str] = "triangle"

    def __post_init__(self) -> None:
        _require_sorted(self.kind, (self.a, self.b, self.c))
        if self.a == self.c:
            raise DefinitionError("Un triangle doit avoir une base de largeur non nulle (a < c).")

    def __call__(self, x: float) -> float:
        if x < self.a or x > self.c:
            return 0.0
        if x == self.b:
            return 1.0
        if x < self.b:
            return (x - self.a) / (self.b - self.a)
        return (self.c - x) / (self.c - self.b)

    def parameters(self) -> tuple[float, ...]:
        return (self.a, self.b, self.c)


@dataclass(frozen=True, slots=True)
class Trapezoidal(MembershipFunction):
    """Trapezoid with feet ``a``, ``d`` and plateau ``[b, c]`` (``a <= b <= c <= d``)."""

    a: float
    b: float
    c: float
    d: float
    kind: ClassVar[str] = "trapezoid"

    def __post_init__(self) -> None:
        _require_sorted(self.kind, (self.a, self.b, self.c, self.d))
        if self.a == self.d:
            raise DefinitionError("Un trapèze doit avoir une base de largeur non nulle (a < d).")

    def __call__(self, x: float) -> float:
        if x < self.a or x > self.d:
            return 0.0
        if self.b <= x <= self.c:
            return 1.0
        if x < self.b:
            return (x - self.a) / (self.b - self.a)
        return (self.d - x) / (self.d - self.c)

    def parameters(self) -> tuple[float, ...]:
        return (self.a, self.b, self.c, self.d)


@dataclass(frozen=True, slots=True)
class RampUp(MembershipFunction):
    """Right shoulder: 0 before ``a``, linear rise, 1 after ``b`` (``a < b``)."""

    a: float
    b: float
    kind: ClassVar[str] = "ramp_up"

    def __post_init__(self) -> None:
        if not self.a < self.b:
            raise DefinitionError(f"ramp_up : il faut a < b (reçu a={self.a}, b={self.b}).")

    def __call__(self, x: float) -> float:
        if x <= self.a:
            return 0.0
        if x >= self.b:
            return 1.0
        return (x - self.a) / (self.b - self.a)

    def parameters(self) -> tuple[float, ...]:
        return (self.a, self.b)


@dataclass(frozen=True, slots=True)
class RampDown(MembershipFunction):
    """Left shoulder: 1 before ``a``, linear fall, 0 after ``b`` (``a < b``)."""

    a: float
    b: float
    kind: ClassVar[str] = "ramp_down"

    def __post_init__(self) -> None:
        if not self.a < self.b:
            raise DefinitionError(f"ramp_down : il faut a < b (reçu a={self.a}, b={self.b}).")

    def __call__(self, x: float) -> float:
        if x <= self.a:
            return 1.0
        if x >= self.b:
            return 0.0
        return (self.b - x) / (self.b - self.a)

    def parameters(self) -> tuple[float, ...]:
        return (self.a, self.b)


@dataclass(frozen=True, slots=True)
class Gaussian(MembershipFunction):
    """Bell curve ``exp(-(x-mean)² / (2σ²))`` (``sigma > 0``)."""

    mean: float
    sigma: float
    kind: ClassVar[str] = "gaussian"

    def __post_init__(self) -> None:
        if self.sigma <= 0:
            raise DefinitionError(f"gaussian : sigma doit être > 0 (reçu {self.sigma}).")

    def __call__(self, x: float) -> float:
        z = (x - self.mean) / self.sigma
        return math.exp(-0.5 * z * z)

    def parameters(self) -> tuple[float, ...]:
        return (self.mean, self.sigma)


@dataclass(frozen=True, slots=True)
class Singleton(MembershipFunction):
    """Crisp value: 1 exactly at ``value``, 0 elsewhere (a classical element).

    Note: a singleton is only visible to grid-based defuzzifiers if ``value`` lies on
    the sampling grid; prefer a narrow :class:`Triangular` for Mamdani outputs.
    """

    value: float
    kind: ClassVar[str] = "singleton"

    def __call__(self, x: float) -> float:
        return 1.0 if x == self.value else 0.0

    def parameters(self) -> tuple[float, ...]:
        return (self.value,)


MEMBERSHIP_REGISTRY: dict[str, type[MembershipFunction]] = {
    cls.kind: cls for cls in (Triangular, Trapezoidal, RampUp, RampDown, Gaussian, Singleton)
}
"""Shapes addressable by name from configuration files (``kind`` → class)."""


def _numeric_parameters(kind: str, params: Sequence[object]) -> list[float]:
    values: list[float] = []
    for param in params:
        if isinstance(param, bool) or not isinstance(param, int | float):
            raise DefinitionError(f"Paramètre non numérique pour '{kind}' : {param!r}.")
        if not math.isfinite(param):
            raise DefinitionError(f"Paramètre non fini pour '{kind}' : {param!r}.")
        values.append(float(param))
    return values


def membership_from_spec(kind: str, params: Sequence[object]) -> MembershipFunction:
    """Factory: build a membership function from a shape name and its parameters.

    >>> membership_from_spec("triangle", [0, 5, 10])(5)
    1.0
    """
    try:
        cls = MEMBERSHIP_REGISTRY[kind.lower()]
    except KeyError as exc:
        known = ", ".join(sorted(MEMBERSHIP_REGISTRY))
        raise DefinitionError(
            f"Forme de fonction d'appartenance inconnue : '{kind}'. Formes connues : {known}."
        ) from exc
    values = _numeric_parameters(kind, params)
    try:
        return cls(*values)
    except TypeError as exc:
        raise DefinitionError(
            f"Nombre de paramètres invalide pour '{kind}' : {list(params)}."
        ) from exc
