"""Triangular norms used to combine truth degrees along a derivation.

In classical resolution a derivation is valid or not; here every step carries a
degree in ``[0, 1]`` and the degree of a derivation is the t-norm of its steps.
Restricted to ``{0, 1}`` every t-norm is the classical conjunction.
"""

from __future__ import annotations

from typing import Protocol, runtime_checkable

from fuzzyprolog.exceptions import ProgramError


@runtime_checkable
class TNorm(Protocol):
    name: str

    def __call__(self, a: float, b: float) -> float: ...


class Minimum:
    name = "min"

    def __call__(self, a: float, b: float) -> float:
        return a if a < b else b


class Product:
    name = "product"

    def __call__(self, a: float, b: float) -> float:
        return a * b


class Lukasiewicz:
    name = "lukasiewicz"

    def __call__(self, a: float, b: float) -> float:
        return max(0.0, a + b - 1.0)


TNORMS: dict[str, TNorm] = {t.name: t for t in (Minimum(), Product(), Lukasiewicz())}
MIN: TNorm = TNORMS["min"]


def tnorm_from_name(name: str) -> TNorm:
    try:
        return TNORMS[name.lower()]
    except KeyError as exc:
        raise ProgramError(
            f"t-norme inconnue : '{name}' (connues : {', '.join(sorted(TNORMS))})."
        ) from exc
