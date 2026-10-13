"""Well-formed fuzzy formulas (the *fbf* of the course, with graded truth values).

The course defines formulas recursively: ``F = p | ¬H | H □ K`` with ``□ ∈ {∧, ∨, …}``.
We mirror that definition with an immutable AST: :class:`Atom`, :class:`Not`,
:class:`And`, :class:`Or`. An :class:`Interpretation` (the course's ``δ``) assigns a
truth degree in ``[0, 1]`` to every atom instead of a value in ``{□, ■}``.

Operator precedence follows the course's convention ``¬ > ∧ > ∨`` and drives both
parsing and the parenthesis-free rendering of formulas.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import Iterator, Mapping
from dataclasses import dataclass
from typing import ClassVar

from fuzzyengine.dsl.syntax import ENGLISH, Syntax
from fuzzyengine.exceptions import EvaluationError
from fuzzyengine.modifiers import Modifier
from fuzzyengine.operators import FuzzyOperators


class Interpretation:
    """Truth-degree assignment ``δ : (variable, terme) → [0, 1]``."""

    __slots__ = ("_degrees",)

    def __init__(self, degrees: Mapping[str, Mapping[str, float]]) -> None:
        self._degrees: dict[str, dict[str, float]] = {
            variable: dict(terms) for variable, terms in degrees.items()
        }

    def degree(self, variable: str, term: str) -> float:
        try:
            return self._degrees[variable][term]
        except KeyError as exc:
            raise EvaluationError(
                f"Aucun degré de vérité pour l'atome '{variable} IS {term}' : "
                "la variable n'a pas été fuzzifiée ou le terme n'existe pas."
            ) from exc

    def variables(self) -> tuple[str, ...]:
        return tuple(self._degrees)

    def as_dict(self) -> dict[str, dict[str, float]]:
        return {variable: dict(terms) for variable, terms in self._degrees.items()}


class Formula(ABC):
    """Node of the formula AST."""

    precedence: ClassVar[int]

    @abstractmethod
    def truth(self, interpretation: Interpretation, operators: FuzzyOperators) -> float:
        """Truth degree of the formula under ``interpretation``."""

    @abstractmethod
    def atoms(self) -> Iterator[Atom]:
        """All atoms occurring in the formula (left-to-right, with repetitions)."""

    @abstractmethod
    def render(self, syntax: Syntax = ENGLISH) -> str:
        """Textual form in the given syntax, with the minimal parentheses."""

    def __str__(self) -> str:
        return self.render(ENGLISH)

    def _child(self, child: Formula, syntax: Syntax) -> str:
        """Render a sub-formula, adding parentheses only when precedence requires it."""
        text = child.render(syntax)
        return f"({text})" if child.precedence < self.precedence else text


@dataclass(frozen=True, slots=True)
class Atom(Formula):
    """Elementary proposition ``variable IS [modifier] term``."""

    variable: str
    term: str
    modifier: Modifier | None = None
    precedence: ClassVar[int] = 4

    def truth(self, interpretation: Interpretation, operators: FuzzyOperators) -> float:
        degree = interpretation.degree(self.variable, self.term)
        return self.modifier(degree) if self.modifier is not None else degree

    def atoms(self) -> Iterator[Atom]:
        yield self

    def render(self, syntax: Syntax = ENGLISH) -> str:
        return f"{self.variable} {syntax.IS} {self._term_text(syntax)}"

    def _term_text(self, syntax: Syntax) -> str:
        if self.modifier is None:
            return self.term
        return f"{syntax.modifier(self.modifier.name)} {self.term}"


@dataclass(frozen=True, slots=True)
class Not(Formula):
    operand: Formula
    precedence: ClassVar[int] = 3

    def truth(self, interpretation: Interpretation, operators: FuzzyOperators) -> float:
        return operators.negation(self.operand.truth(interpretation, operators))

    def atoms(self) -> Iterator[Atom]:
        yield from self.operand.atoms()

    def render(self, syntax: Syntax = ENGLISH) -> str:
        if isinstance(self.operand, Atom):
            atom = self.operand
            return f"{atom.variable} {syntax.IS_NOT} {atom._term_text(syntax)}"
        return f"{syntax.NOT} {self._child(self.operand, syntax)}"


@dataclass(frozen=True, slots=True)
class And(Formula):
    left: Formula
    right: Formula
    precedence: ClassVar[int] = 2

    def truth(self, interpretation: Interpretation, operators: FuzzyOperators) -> float:
        return operators.conjunction(
            self.left.truth(interpretation, operators),
            self.right.truth(interpretation, operators),
        )

    def atoms(self) -> Iterator[Atom]:
        yield from self.left.atoms()
        yield from self.right.atoms()

    def render(self, syntax: Syntax = ENGLISH) -> str:
        return f"{self._child(self.left, syntax)} {syntax.AND} {self._child(self.right, syntax)}"


@dataclass(frozen=True, slots=True)
class Or(Formula):
    left: Formula
    right: Formula
    precedence: ClassVar[int] = 1

    def truth(self, interpretation: Interpretation, operators: FuzzyOperators) -> float:
        return operators.disjunction(
            self.left.truth(interpretation, operators),
            self.right.truth(interpretation, operators),
        )

    def atoms(self) -> Iterator[Atom]:
        yield from self.left.atoms()
        yield from self.right.atoms()

    def render(self, syntax: Syntax = ENGLISH) -> str:
        return f"{self._child(self.left, syntax)} {syntax.OR} {self._child(self.right, syntax)}"


def conjunction(*formulas: Formula) -> Formula:
    """Left-associative ∧ of several formulas (helper for builders)."""
    if not formulas:
        raise ValueError("conjunction() requiert au moins une formule.")
    result = formulas[0]
    for formula in formulas[1:]:
        result = And(result, formula)
    return result
