"""Answers of a query and their proofs."""

from __future__ import annotations

from dataclasses import dataclass

from fuzzyprolog.terms import Term, Var, render


@dataclass(frozen=True, slots=True)
class ProofStep:
    """One resolution step: the goal, how it was resolved and the degrees involved."""

    level: int
    """Nesting level of the goal (0 = query goal, 1 = body of the clause proving it...)."""
    goal: str
    via: str
    degree: float
    """Degree contributed by this step (unifier × clause, or built-in degree)."""
    cumulative: float
    """Degree of the derivation after this step."""
    similarities: tuple[tuple[Term, Term, float], ...] = ()

    def render(self) -> str:
        indent = "  " * self.level
        line = f"{indent}{self.goal}  <-  {self.via}"
        if self.degree < 1.0:
            line += f"  [{self.degree:.2f}]"
        for a, b, d in self.similarities:
            line += f"\n{indent}    similarité {render(a)} ~ {render(b)} ({d:.2f})"
        return line


@dataclass(frozen=True, slots=True)
class Solution:
    bindings: dict[str, Term]
    """Value of every query variable (an unbound variable maps to a :class:`Var`)."""
    degree: float
    steps: tuple[ProofStep, ...] = ()

    def bound(self) -> dict[str, Term]:
        return {name: term for name, term in self.bindings.items() if not isinstance(term, Var)}

    def __str__(self) -> str:
        bound = self.bound()
        if not bound:
            return f"oui ({self.degree:.2f})"
        answer = ", ".join(f"{name} = {render(term)}" for name, term in bound.items())
        return f"{answer} ({self.degree:.2f})"

    def explain(self) -> str:
        """The derivation as an indented tree of resolution steps."""
        if not self.steps:
            return f"{self}\n  (aucune étape enregistrée)"
        lines = [str(self)]
        lines.extend(step.render() for step in self.steps)
        return "\n".join(lines)
