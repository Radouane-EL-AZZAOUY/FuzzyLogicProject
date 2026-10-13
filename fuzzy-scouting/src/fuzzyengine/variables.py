"""Fuzzy sets (linguistic terms) and linguistic variables.

In the course a predicate ``P`` of arity 1 is an application ``D → {Vrai, Faux}``.
A fuzzy set generalises it to ``μ_P : D → [0, 1]``; a linguistic variable groups
the fuzzy predicates that can be said about one quantity (e.g. *vitesse* ∈
{lente, moyenne, rapide}).
"""

from __future__ import annotations

from collections.abc import Iterator
from dataclasses import dataclass, field

from fuzzyengine.exceptions import DefinitionError, KnowledgeBaseError
from fuzzyengine.membership import MembershipFunction
from fuzzyengine.universe import Universe


@dataclass(frozen=True, slots=True)
class FuzzySet:
    """A linguistic term: a label and its membership function."""

    label: str
    membership: MembershipFunction

    def __post_init__(self) -> None:
        if not self.label or not self.label.strip():
            raise DefinitionError("Le libellé d'un terme flou ne peut pas être vide.")

    def degree(self, x: float) -> float:
        """Membership degree of ``x``, clipped to ``[0, 1]`` for numerical safety."""
        return min(1.0, max(0.0, self.membership(x)))


@dataclass(frozen=True, slots=True)
class LinguisticVariable:
    """A named quantity, its universe of discourse and its linguistic terms."""

    name: str
    universe: Universe
    terms: tuple[FuzzySet, ...]
    description: str = ""
    unit: str = ""
    _index: dict[str, FuzzySet] = field(init=False, repr=False, compare=False)

    def __post_init__(self) -> None:
        if not self.name or not self.name.strip():
            raise DefinitionError("Le nom d'une variable linguistique ne peut pas être vide.")
        if not self.terms:
            raise DefinitionError(f"La variable '{self.name}' doit avoir au moins un terme.")
        index: dict[str, FuzzySet] = {}
        for term in self.terms:
            if term.label in index:
                raise DefinitionError(
                    f"Terme '{term.label}' défini deux fois pour la variable '{self.name}'."
                )
            index[term.label] = term
        object.__setattr__(self, "_index", index)

    def __iter__(self) -> Iterator[FuzzySet]:
        return iter(self.terms)

    @property
    def labels(self) -> tuple[str, ...]:
        return tuple(term.label for term in self.terms)

    def has_term(self, label: str) -> bool:
        return label in self._index

    def term(self, label: str) -> FuzzySet:
        try:
            return self._index[label]
        except KeyError as exc:
            raise KnowledgeBaseError(
                f"Terme inconnu '{label}' pour la variable '{self.name}' "
                f"(termes connus : {', '.join(self.labels)})."
            ) from exc

    def fuzzify(self, x: float) -> dict[str, float]:
        """Degrees of membership of ``x`` in every term (the fuzzy *interpretation* of x)."""
        return {term.label: term.degree(x) for term in self.terms}
