"""Fuzzy connectives: t-norms (∧), t-conorms (∨), complements (¬) and implications (→).

They generalise the truth tables of the course. Restricted to ``{0, 1}`` every family
below reproduces the classical tables exactly (see ``tests/engine/test_operators.py``),
which makes fuzzy logic a *conservative extension* of propositional logic.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from typing import Protocol, TypeVar, runtime_checkable

from fuzzyengine.exceptions import DefinitionError

T = TypeVar("T")


@runtime_checkable
class BinaryOperator(Protocol):
    """A commutative, associative, monotone binary operator on ``[0, 1]``."""

    name: str

    def __call__(self, a: float, b: float) -> float: ...


@runtime_checkable
class UnaryOperator(Protocol):
    name: str

    def __call__(self, a: float) -> float: ...


@runtime_checkable
class Implication(Protocol):
    """Combines a rule's firing strength with a consequent's membership degree."""

    name: str

    def __call__(self, strength: float, degree: float) -> float: ...


# --- t-norms (conjunction) ---------------------------------------------------


class MinimumTNorm:
    """Zadeh conjunction ``min(a, b)``."""

    name = "min"

    def __call__(self, a: float, b: float) -> float:
        return min(a, b)


class ProductTNorm:
    """Probabilistic conjunction ``a · b``."""

    name = "product"

    def __call__(self, a: float, b: float) -> float:
        return a * b


class LukasiewiczTNorm:
    """Bounded difference ``max(0, a + b - 1)``."""

    name = "lukasiewicz"

    def __call__(self, a: float, b: float) -> float:
        return max(0.0, a + b - 1.0)


# --- t-conorms (disjunction) --------------------------------------------------


class MaximumSNorm:
    """Zadeh disjunction ``max(a, b)``."""

    name = "max"

    def __call__(self, a: float, b: float) -> float:
        return max(a, b)


class ProbabilisticSumSNorm:
    """``a + b - a·b``."""

    name = "probabilistic_sum"

    def __call__(self, a: float, b: float) -> float:
        return a + b - a * b


class BoundedSumSNorm:
    """``min(1, a + b)``."""

    name = "bounded_sum"

    def __call__(self, a: float, b: float) -> float:
        return min(1.0, a + b)


# --- complements (negation) --------------------------------------------------


class StandardComplement:
    """``1 - a``."""

    name = "standard"

    def __call__(self, a: float) -> float:
        return 1.0 - a


# --- implications (Mamdani-style, used to clip/scale consequents) -------------


class MinimumImplication:
    """Mamdani implication: consequent clipped at the firing strength ``min(α, μ)``."""

    name = "min"

    def __call__(self, strength: float, degree: float) -> float:
        return min(strength, degree)


class ProductImplication:
    """Larsen implication: consequent scaled by the firing strength ``α · μ``."""

    name = "product"

    def __call__(self, strength: float, degree: float) -> float:
        return strength * degree


# --- operator families ---------------------------------------------------------


@dataclass(frozen=True, slots=True)
class FuzzyOperators:
    """The triple (∧, ∨, ¬) used to evaluate formulas."""

    conjunction: BinaryOperator
    disjunction: BinaryOperator
    negation: UnaryOperator
    name: str = "custom"


ZADEH = FuzzyOperators(MinimumTNorm(), MaximumSNorm(), StandardComplement(), name="zadeh")
PROBABILISTIC = FuzzyOperators(
    ProductTNorm(), ProbabilisticSumSNorm(), StandardComplement(), name="probabilistic"
)
LUKASIEWICZ = FuzzyOperators(
    LukasiewiczTNorm(), BoundedSumSNorm(), StandardComplement(), name="lukasiewicz"
)

OPERATOR_FAMILIES: dict[str, FuzzyOperators] = {
    ZADEH.name: ZADEH,
    PROBABILISTIC.name: PROBABILISTIC,
    LUKASIEWICZ.name: LUKASIEWICZ,
}

IMPLICATIONS: dict[str, Implication] = {
    MinimumImplication.name: MinimumImplication(),
    ProductImplication.name: ProductImplication(),
}

AGGREGATIONS: dict[str, BinaryOperator] = {
    MaximumSNorm.name: MaximumSNorm(),
    ProbabilisticSumSNorm.name: ProbabilisticSumSNorm(),
    BoundedSumSNorm.name: BoundedSumSNorm(),
}


def _lookup(registry: Mapping[str, T], name: str, what: str) -> T:
    try:
        return registry[name.lower()]
    except KeyError as exc:
        raise DefinitionError(
            f"{what} inconnu(e) : '{name}'. Valeurs connues : {', '.join(sorted(registry))}."
        ) from exc


def operators_from_name(name: str) -> FuzzyOperators:
    return _lookup(OPERATOR_FAMILIES, name, "Famille d'opérateurs")


def implication_from_name(name: str) -> Implication:
    return _lookup(IMPLICATIONS, name, "Implication")


def aggregation_from_name(name: str) -> BinaryOperator:
    return _lookup(AGGREGATIONS, name, "Agrégation")
