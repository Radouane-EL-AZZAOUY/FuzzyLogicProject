"""Similarity relations between constants (the fuzzy twist on unification).

Classical unification fails on two distinct constants (``mohamed`` vs ``mohammed``).
Under a *similarity relation* ``R`` — reflexive, symmetric and max-min transitive —
two constants unify with degree ``R(a, b)`` (Sessa's weak unification, used by
Bousi~Prolog). Declarations come from the program (``a ~ b @ 0.9.``) and the closure
is computed lazily.
"""

from __future__ import annotations

from collections.abc import Iterator

from fuzzyprolog.exceptions import ProgramError
from fuzzyprolog.terms import Number, Term, is_constant, render


class SimilarityRelation:
    def __init__(self, transitive: bool = True) -> None:
        self._declared: dict[tuple[Term, Term], float] = {}
        self._closure: dict[tuple[Term, Term], float] | None = None
        self.transitive = transitive

    def declare(self, a: Term, b: Term, degree: float) -> None:
        if not (is_constant(a) and is_constant(b)):
            raise ProgramError(
                f"Une similarité ne relie que des constantes : {render(a)} ~ {render(b)}."
            )
        if not 0.0 < degree <= 1.0:
            raise ProgramError(
                f"Degré de similarité hors ]0, 1] : {degree} ({render(a)} ~ {render(b)})."
            )
        if isinstance(a, Number) or isinstance(b, Number):
            raise ProgramError(
                "Les nombres se comparent par valeur, pas par similarité : "
                f"{render(a)} ~ {render(b)}."
            )
        if a == b:
            return
        key = (a, b) if _key(a) <= _key(b) else (b, a)
        self._declared[key] = max(degree, self._declared.get(key, 0.0))
        self._closure = None

    def __len__(self) -> int:
        return len(self._declared)

    def declarations(self) -> Iterator[tuple[Term, Term, float]]:
        for (a, b), degree in self._declared.items():
            yield a, b, degree

    def degree(self, a: Term, b: Term) -> float:
        """``R(a, b)``: 1 for equal constants, 0 when unrelated."""
        if a == b:
            return 1.0
        if not self._declared:
            return 0.0
        table = self._table()
        key = (a, b) if _key(a) <= _key(b) else (b, a)
        return table.get(key, 0.0)

    def related(self, term: Term) -> list[Term]:
        """Constants similar to ``term`` (degree > 0), excluding ``term`` itself."""
        if not self._declared:
            return []
        return [
            other
            for (a, b) in self._table()
            for other in ((b,) if a == term else (a,) if b == term else ())
        ]

    def _table(self) -> dict[tuple[Term, Term], float]:
        if self._closure is None:
            self._closure = self._max_min_closure() if self.transitive else dict(self._declared)
        return self._closure

    def _max_min_closure(self) -> dict[tuple[Term, Term], float]:
        """Floyd-Warshall with (max, min): transitive closure of a fuzzy relation."""
        nodes: list[Term] = []
        seen: set[Term] = set()
        for a, b in self._declared:
            for node in (a, b):
                if node not in seen:
                    seen.add(node)
                    nodes.append(node)
        degree: dict[tuple[Term, Term], float] = {}
        for (a, b), d in self._declared.items():
            degree[(a, b)] = d
            degree[(b, a)] = d
        for k in nodes:
            for i in nodes:
                dik = degree.get((i, k), 0.0)
                if dik == 0.0 or i == k:
                    continue
                for j in nodes:
                    if j in (i, k):
                        continue
                    through = min(dik, degree.get((k, j), 0.0))
                    if through > degree.get((i, j), 0.0):
                        degree[(i, j)] = through
        closure: dict[tuple[Term, Term], float] = {}
        for (a, b), d in degree.items():
            if _key(a) <= _key(b):
                closure[(a, b)] = d
        return closure


def _key(term: Term) -> tuple[str, str]:
    return (type(term).__name__, render(term))
