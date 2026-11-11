"""Unification with similarity (course, *Algorithme d'unification de 2 atomes A et B*).

The algorithm follows the course step by step: walk both terms in parallel, find the
leftmost disagreement, fail if neither side is a variable *or* if the variable occurs
in the other term (occurs check), otherwise extend the substitution. The only change
is the treatment of two different constants: instead of failing, the pair is looked
up in the similarity relation and the unification succeeds with that degree.
"""

from __future__ import annotations

from dataclasses import dataclass

from fuzzyprolog.similarity import SimilarityRelation
from fuzzyprolog.substitution import Substitution
from fuzzyprolog.terms import Atom, Number, String, Struct, Term, Var
from fuzzyprolog.tnorms import MIN, TNorm


@dataclass(frozen=True, slots=True)
class Unifier:
    substitution: Substitution
    degree: float
    """1.0 for a classical (syntactic) unification; lower when similarities were used."""
    similarities: tuple[tuple[Term, Term, float], ...] = ()
    """The constant pairs matched by similarity, for explanations."""


def occurs(variable: Var, term: Term, subst: Substitution) -> bool:
    stack = [term]
    while stack:
        current = subst.walk(stack.pop())
        if current == variable:
            return True
        if isinstance(current, Struct):
            stack.extend(current.args)
    return False


def unify(
    a: Term,
    b: Term,
    subst: Substitution,
    similarity: SimilarityRelation | None = None,
    tnorm: TNorm = MIN,
    occurs_check: bool = True,
    threshold: float = 0.0,
) -> Unifier | None:
    """Most general unifier of ``a`` and ``b`` extending ``subst``, or ``None``."""
    degree = 1.0
    matches: list[tuple[Term, Term, float]] = []
    stack: list[tuple[Term, Term]] = [(a, b)]
    while stack:
        x, y = stack.pop()
        x = subst.walk(x)
        y = subst.walk(y)
        if x == y:
            continue
        if isinstance(x, Var):
            if occurs_check and occurs(x, y, subst):
                return None
            subst = subst.bind(x, y)
            continue
        if isinstance(y, Var):
            if occurs_check and occurs(y, x, subst):
                return None
            subst = subst.bind(y, x)
            continue
        if isinstance(x, Struct) and isinstance(y, Struct):
            if x.functor != y.functor or x.arity != y.arity:
                return None
            stack.extend(zip(reversed(x.args), reversed(y.args), strict=True))
            continue
        if isinstance(x, Number) and isinstance(y, Number):
            if x.value == y.value:
                continue
            return None
        if isinstance(x, Atom | String) and isinstance(y, Atom | String):
            sim = similarity.degree(x, y) if similarity is not None else 0.0
            if sim <= 0.0:
                return None
            degree = tnorm(degree, sim)
            if degree < threshold or degree <= 0.0:
                return None
            matches.append((x, y, sim))
            continue
        return None
    return Unifier(subst, degree, tuple(matches))
