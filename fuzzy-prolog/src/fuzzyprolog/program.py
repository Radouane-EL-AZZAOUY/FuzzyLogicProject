"""Clauses and programs.

A clause ``Tête :- C1, …, Cn @ d`` is a Horn clause (course, *Les règles*) carrying a
truth degree ``d`` (1 when omitted). A program is an ordered set of clauses — the
axioms of the formal system — plus a similarity relation and execution settings
coming from directives.
"""

from __future__ import annotations

from collections.abc import Iterable, Iterator
from dataclasses import dataclass, field

from fuzzyprolog.exceptions import ProgramError
from fuzzyprolog.similarity import SimilarityRelation
from fuzzyprolog.substitution import Renamer, Substitution, variables_of
from fuzzyprolog.terms import (
    Atom,
    Number,
    String,
    Struct,
    Term,
    Var,
    indicator_of,
    is_callable,
    render,
)
from fuzzyprolog.tnorms import MIN, TNorm, tnorm_from_name


@dataclass(frozen=True, slots=True)
class Clause:
    head: Term
    body: tuple[Term, ...]
    degree: float = 1.0
    line: int = 0
    sequence: int = 0
    """Position in the program (clause order matters, as in Prolog)."""
    ground: bool = field(init=False, default=False, compare=False)
    """``True`` when the clause has no variable: renaming it is then unnecessary."""

    def __post_init__(self) -> None:
        if not is_callable(self.head):
            raise ProgramError(f"Tête de clause invalide : {render(self.head)}.")
        if isinstance(self.head, Struct) and self.head.functor in CONTROL_FUNCTORS:
            raise ProgramError(f"Impossible de définir le connecteur '{self.head.functor}'.")
        if not 0.0 < self.degree <= 1.0:
            raise ProgramError(
                f"Degré de clause hors ]0, 1] : {self.degree} ({render(self.head)})."
            )
        for goal in self.body:
            if not (isinstance(goal, Var) or is_callable(goal)):
                raise ProgramError(
                    f"But non appelable dans le corps de {render(self.head)} : {render(goal)}."
                )
        has_variables = bool(variables_of(self.head)) or any(variables_of(g) for g in self.body)
        object.__setattr__(self, "ground", not has_variables)

    @property
    def indicator(self) -> str:
        return indicator_of(self.head)

    @property
    def is_fact(self) -> bool:
        return not self.body

    def rename(self, renamer: Renamer) -> Clause:
        """A copy with fresh variables (θ of the course); ground clauses are returned as is."""
        if self.ground:
            return self
        mapping: dict[Var, Var] = {}
        head = renamer.rename(self.head, mapping)
        body = tuple(renamer.rename(goal, mapping) for goal in self.body)
        return Clause(head, body, self.degree, self.line, self.sequence)

    def __str__(self) -> str:
        suffix = "" if self.degree == 1.0 else f" @ {self.degree:g}"
        if not self.body:
            return f"{render(self.head)}{suffix}."
        body = ", ".join(render(g) for g in self.body)
        return f"{render(self.head)} :- {body}{suffix}."


CONTROL_FUNCTORS = frozenset({",", ";", "->", "\\+", "!", "call", "findall", "not"})

IndexKey = tuple[str, object] | tuple[str, str, int]


def _index_key(term: Term) -> IndexKey | None:
    """First-argument indexing key of a constant or structure (``None`` for variables)."""
    if isinstance(term, Atom):
        return ("atom", term.name)
    if isinstance(term, String):
        return ("string", term.value)
    if isinstance(term, Number):
        return ("number", term.value)
    if isinstance(term, Struct):
        return ("struct", term.functor, term.arity)
    return None


INDEXED_POSITIONS = 2
"""Arguments indexed (first two): ``fiche(Id, …)`` and ``bloc(Key, Id)`` are both O(1)."""


@dataclass
class _Predicate:
    clauses: list[Clause] = field(default_factory=list)
    indexes: list[dict[IndexKey, list[Clause]]] = field(
        default_factory=lambda: [{} for _ in range(INDEXED_POSITIONS)]
    )
    unindexed: list[list[Clause]] = field(
        default_factory=lambda: [[] for _ in range(INDEXED_POSITIONS)]
    )
    """Per position: clauses whose argument there is a variable (match any key)."""

    def add(self, clause: Clause) -> None:
        self.clauses.append(clause)
        args = clause.head.args if isinstance(clause.head, Struct) else ()
        for position in range(min(INDEXED_POSITIONS, len(args))):
            key = _index_key(args[position])
            if key is None:
                self.unindexed[position].append(clause)
            else:
                self.indexes[position].setdefault(key, []).append(clause)

    def candidates(
        self, goal: Term, subst: Substitution, similarity: SimilarityRelation
    ) -> list[Clause]:
        """Clauses that may unify with ``goal``, in program order.

        The first *bound* argument among the indexed positions selects the clauses
        indexed under the same constant, plus those indexed under a *similar*
        constant (so that similarity-based unification keeps working) and the
        variable-headed ones. With no bound indexed argument, every clause is returned.
        """
        if not isinstance(goal, Struct):
            return self.clauses
        for position in range(min(INDEXED_POSITIONS, goal.arity)):
            index = self.indexes[position]
            if not index:
                continue
            value = subst.walk(goal.args[position])
            key = _index_key(value)
            if key is None:
                continue
            matched = list(index.get(key, ()))
            if isinstance(value, Atom | String):
                for neighbour in similarity.related(value):
                    neighbour_key = _index_key(neighbour)
                    if neighbour_key is not None:
                        matched.extend(index.get(neighbour_key, ()))
            unindexed = self.unindexed[position]
            if not unindexed and len(matched) <= 1:
                return matched
            return sorted(matched + unindexed, key=lambda c: c.sequence)
        return self.clauses


@dataclass(frozen=True, slots=True)
class Settings:
    tnorm: TNorm = MIN
    lambda_cut: float = 0.0
    """Derivations whose degree drops below this threshold are abandoned."""
    max_depth: int = 1000
    """Maximum number of resolution steps along one derivation (bounded by Python's stack)."""
    occurs_check: bool = True

    def with_(self, **changes: object) -> Settings:
        values = {
            "tnorm": self.tnorm,
            "lambda_cut": self.lambda_cut,
            "max_depth": self.max_depth,
            "occurs_check": self.occurs_check,
        }
        values.update(changes)
        return Settings(**values)  # type: ignore[arg-type]


class Program:
    """Ordered clauses with first-argument indexing, similarities and settings."""

    def __init__(self) -> None:
        self._predicates: dict[str, _Predicate] = {}
        self._sequence = 0
        self.similarity = SimilarityRelation()
        self.settings = Settings()

    # --- building --------------------------------------------------------------

    def add_clause(self, clause: Clause) -> None:
        self._sequence += 1
        stamped = Clause(clause.head, clause.body, clause.degree, clause.line, self._sequence)
        self._predicates.setdefault(stamped.indicator, _Predicate()).add(stamped)

    def add_fact(self, head: Term, degree: float = 1.0) -> None:
        self.add_clause(Clause(head, (), degree))

    def add_similarity(self, a: Term, b: Term, degree: float) -> None:
        self.similarity.declare(a, b, degree)

    def apply_directive(self, directive: Term) -> None:
        """``:- lambda_cut(0.5).``, ``:- tnorm(product).``, ``:- max_depth(500).``,
        ``:- occurs_check(false).``, ``:- similar(a, b, 0.8).``, ``:- transitive(false).``"""
        if not isinstance(directive, Struct):
            raise ProgramError(f"Directive inconnue : {render(directive)}.")
        name, args = directive.functor, directive.args
        try:
            if name == "lambda_cut" and len(args) == 1:
                value = _number(args[0])
                if not 0.0 <= value <= 1.0:
                    raise ProgramError("lambda_cut doit être dans [0, 1].")
                self.settings = self.settings.with_(lambda_cut=value)
            elif name == "tnorm" and len(args) == 1 and isinstance(args[0], Atom):
                self.settings = self.settings.with_(tnorm=tnorm_from_name(args[0].name))
            elif name == "max_depth" and len(args) == 1:
                self.settings = self.settings.with_(max_depth=int(_number(args[0])))
            elif name == "occurs_check" and len(args) == 1 and isinstance(args[0], Atom):
                self.settings = self.settings.with_(occurs_check=args[0].name == "true")
            elif name == "transitive" and len(args) == 1 and isinstance(args[0], Atom):
                self.similarity.transitive = args[0].name == "true"
            elif name == "similar" and len(args) == 3:
                self.add_similarity(args[0], args[1], _number(args[2]))
            else:
                raise ProgramError(f"Directive inconnue : {render(directive)}.")
        except ValueError as exc:
            raise ProgramError(f"Directive invalide {render(directive)} : {exc}") from exc

    def extend(self, other: Program) -> None:
        """Append every clause and similarity of ``other`` (used for the prelude)."""
        for clause in other.clauses():
            self.add_clause(clause)
        for a, b, degree in other.similarity.declarations():
            self.add_similarity(a, b, degree)

    # --- querying ---------------------------------------------------------------

    def clauses(self) -> Iterator[Clause]:
        ordered = sorted(
            (c for p in self._predicates.values() for c in p.clauses), key=lambda c: c.sequence
        )
        yield from ordered

    def predicates(self) -> list[str]:
        return sorted(self._predicates)

    def defines(self, indicator: str) -> bool:
        return indicator in self._predicates

    def candidates(self, goal: Term, subst: Substitution) -> list[Clause]:
        predicate = self._predicates.get(indicator_of(goal))
        if predicate is None:
            return []
        return predicate.candidates(goal, subst, self.similarity)

    def __len__(self) -> int:
        return sum(len(p.clauses) for p in self._predicates.values())

    def __iter__(self) -> Iterator[Clause]:
        return self.clauses()

    @classmethod
    def from_clauses(cls, clauses: Iterable[Clause]) -> Program:
        program = cls()
        for clause in clauses:
            program.add_clause(clause)
        return program


def _number(term: Term) -> float:
    if isinstance(term, Number):
        return float(term.value)
    raise ValueError(f"nombre attendu, reçu {render(term)}")
