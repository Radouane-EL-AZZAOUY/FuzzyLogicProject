"""Substitutions ``σ = {(X | t), …}`` (course, *Unification*).

A substitution is a finite set of pairs *variable → term*. Applying it to a term
replaces every bound variable by its value, recursively. Instances are immutable:
:meth:`Substitution.bind` returns a new substitution, which makes backtracking
trivial (an abandoned branch simply drops its substitution).
"""

from __future__ import annotations

from collections.abc import Iterable, Iterator
from dataclasses import dataclass, field

from fuzzyprolog.terms import Struct, Term, Var


@dataclass(frozen=True, slots=True)
class Substitution:
    _bindings: dict[Var, Term] = field(default_factory=dict)

    def __len__(self) -> int:
        return len(self._bindings)

    def __contains__(self, variable: Var) -> bool:
        return variable in self._bindings

    def __iter__(self) -> Iterator[tuple[Var, Term]]:
        return iter(self._bindings.items())

    def bind(self, variable: Var, term: Term) -> Substitution:
        """``σ ∪ {(variable | term)}`` as a new substitution."""
        bindings = dict(self._bindings)
        bindings[variable] = term
        return Substitution(bindings)

    def walk(self, term: Term) -> Term:
        """Follow variable bindings until a non-variable or an unbound variable."""
        while isinstance(term, Var):
            bound = self._bindings.get(term)
            if bound is None:
                return term
            term = bound
        return term

    def resolve(self, term: Term) -> Term:
        """Apply the substitution deeply (``t σ`` in the course's notation)."""
        term = self.walk(term)
        if isinstance(term, Struct):
            return Struct(term.functor, tuple(self.resolve(a) for a in term.args))
        return term

    def restrict(self, variables: Iterable[Var]) -> dict[str, Term]:
        """Fully resolved values of the given (query) variables, keyed by name."""
        return {v.name: self.resolve(v) for v in variables if v.name != "_"}


EMPTY = Substitution()


def variables_of(term: Term) -> list[Var]:
    """Distinct variables of a term, in order of first occurrence."""
    found: list[Var] = []
    seen: set[Var] = set()
    stack = [term]
    while stack:
        current = stack.pop()
        if isinstance(current, Var):
            if current not in seen:
                seen.add(current)
                found.append(current)
        elif isinstance(current, Struct):
            stack.extend(reversed(current.args))
    return found


class Renamer:
    """Produces fresh variables (the renaming substitution θ of the course)."""

    def __init__(self, start: int = 1) -> None:
        self._counter = start

    def fresh_index(self) -> int:
        self._counter += 1
        return self._counter

    def rename(self, term: Term, mapping: dict[Var, Var]) -> Term:
        if isinstance(term, Var):
            fresh = mapping.get(term)
            if fresh is None:
                fresh = Var(term.name, self.fresh_index())
                mapping[term] = fresh
            return fresh
        if isinstance(term, Struct):
            return Struct(term.functor, tuple(self.rename(a, mapping) for a in term.args))
        return term
