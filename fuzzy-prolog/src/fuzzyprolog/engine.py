"""Graded SLD resolution (the reasoning of Prolog described in the course, with degrees).

The course describes Prolog's search: a *reasoning point* is a list of goals and a
list of substitutions; take the leftmost goal, find the first untried rule whose head
unifies with it, replace the goal by the rule's body and propagate the substitution;
on failure, *backtrack* to the most recent choice point. This engine implements that
depth-first search with Python generators (every generator is a choice point) and adds:

* a **truth degree** propagated along the derivation (t-norm of clause degrees,
  unification degrees and graded built-ins);
* a **λ-cut**: derivations whose degree drops below ``lambda_cut`` are abandoned;
* the **cut** (``!``), **negation as failure** (``\\+``, with degree ``1 − sup``),
  ``call/N`` and ``findall/3``;
* an optional **proof trace** for explanations.
"""

from __future__ import annotations

import sys
from collections.abc import Callable, Iterator, Sequence
from dataclasses import dataclass

from fuzzyprolog.builtins import BUILTINS, Builtin
from fuzzyprolog.exceptions import DepthLimitError, ExecutionError, InstantiationError
from fuzzyprolog.parser import parse_query
from fuzzyprolog.program import Clause, Program, Settings
from fuzzyprolog.solution import ProofStep, Solution
from fuzzyprolog.substitution import EMPTY, Renamer, Substitution, variables_of
from fuzzyprolog.terms import (
    CUT,
    FAIL,
    TRUE,
    Atom,
    Struct,
    Term,
    Var,
    indicator_of,
    make_list,
    render,
)
from fuzzyprolog.unification import unify


@dataclass(frozen=True, slots=True)
class Goal:
    """A goal to prove, the cut barrier of the clause it belongs to and its nesting level."""

    term: Term
    barrier: int
    level: int


Goals = tuple[Goal, ...]


@dataclass(frozen=True, slots=True)
class _Trace:
    """Persistent linked list of proof steps (sharing tails between branches is free)."""

    step: ProofStep
    previous: _Trace | None

    def materialize(self) -> tuple[ProofStep, ...]:
        steps: list[ProofStep] = []
        node: _Trace | None = self
        while node is not None:
            steps.append(node.step)
            node = node.previous
        steps.reverse()
        return tuple(steps)


Trace = _Trace | None


@dataclass(frozen=True, slots=True)
class _Answer:
    substitution: Substitution
    degree: float
    steps: Trace


@dataclass(frozen=True, slots=True)
class _CutDone:
    """Signal travelling up the generators: 'a cut owned by *barrier* was executed'."""

    barrier: int


_Item = _Answer | _CutDone


class Engine:
    def __init__(
        self,
        program: Program,
        settings: Settings | None = None,
        builtins: dict[str, Builtin] | None = None,
        trace: bool = True,
        output: Callable[[str], None] | None = None,
    ) -> None:
        self.program = program
        self.settings = settings or program.settings
        self.builtins: dict[str, Builtin] = {**BUILTINS, **(builtins or {})}
        self.trace = trace
        self.output: Callable[[str], None] = output or (lambda text: print(text, end=""))
        self._renamer = Renamer()
        self._barrier = 0
        self._unpruned: Engine | None = None
        # Each resolution step nests ~4-5 generator frames: keep Python's limit above that.
        needed = 6 * self.settings.max_depth + 500
        if sys.getrecursionlimit() < needed:
            sys.setrecursionlimit(needed)

    # --- public API -----------------------------------------------------------------

    def query(self, query: str | Sequence[Term], limit: int | None = None) -> Iterator[Solution]:
        """Solutions of a query (text or goals), in Prolog order."""
        goals = parse_query(query) if isinstance(query, str) else tuple(query)
        variables: list[Var] = []
        for goal in goals:
            for variable in variables_of(goal):
                if variable not in variables and not variable.name.startswith("_"):
                    variables.append(variable)
        barrier = self._new_barrier()
        start = tuple(Goal(g, barrier, 0) for g in goals)
        for produced, item in enumerate(self._solve(start, EMPTY, 1.0, 0, None), start=1):
            if isinstance(item, _CutDone):
                return
            steps = item.steps.materialize() if item.steps is not None else ()
            yield Solution(item.substitution.restrict(variables), item.degree, steps)
            if limit is not None and produced >= limit:
                return

    def solve_all(
        self, goal: Term, subst: Substitution = EMPTY
    ) -> list[tuple[Substitution, float]]:
        """Every solution of ``goal`` as (substitution, degree), without trace."""
        barrier = self._new_barrier()
        results: list[tuple[Substitution, float]] = []
        for item in self._solve((Goal(goal, barrier, 0),), subst, 1.0, 0, None, trace=False):
            if isinstance(item, _CutDone):
                break
            results.append((item.substitution, item.degree))
        return results

    def best_degree(self, goal: Term, subst: Substitution = EMPTY) -> float:
        """``sup`` of the degrees of the solutions of ``goal`` (0 if it fails).

        Computed **without** the λ-cut so that ``\\+ G = 1 − sup`` stays sound: a pruning
        threshold must never change the degree of a surviving answer.
        """
        engine = self._without_lambda_cut()
        best = 0.0
        barrier = engine._new_barrier()
        for item in engine._solve((Goal(goal, barrier, 0),), subst, 1.0, 0, None, trace=False):
            if isinstance(item, _CutDone):
                break
            best = max(best, item.degree)
            if best >= 1.0:
                break
        return best

    def succeeds(self, query: str | Sequence[Term]) -> bool:
        return next(self.query(query, limit=1), None) is not None

    # --- resolution ---------------------------------------------------------------------

    def _without_lambda_cut(self) -> Engine:
        if self.settings.lambda_cut == 0.0:
            return self
        if self._unpruned is None:
            self._unpruned = Engine(
                self.program,
                self.settings.with_(lambda_cut=0.0),
                self.builtins,
                trace=False,
                output=self.output,
            )
            self._unpruned._renamer = self._renamer  # fresh variables stay globally unique
        return self._unpruned

    def _new_barrier(self) -> int:
        self._barrier += 1
        return self._barrier

    def _combine(self, degree: float, step: float) -> float | None:
        combined = self.settings.tnorm(degree, step)
        if combined <= 0.0 or combined < self.settings.lambda_cut:
            return None
        return combined

    def _record(
        self,
        steps: Trace,
        trace: bool,
        goal: Goal,
        subst: Substitution,
        via: str,
        degree: float,
        cumulative: float,
        similarities: tuple[tuple[Term, Term, float], ...] = (),
    ) -> Trace:
        if not trace:
            return steps
        step = ProofStep(
            goal.level, render(subst.resolve(goal.term)), via, degree, cumulative, similarities
        )
        return _Trace(step, steps)

    def _solve(
        self,
        goals: Goals,
        subst: Substitution,
        degree: float,
        depth: int,
        steps: Trace,
        trace: bool | None = None,
    ) -> Iterator[_Item]:
        trace = self.trace if trace is None else trace
        if not goals:
            yield _Answer(subst, degree, steps)
            return
        if depth > self.settings.max_depth:
            raise DepthLimitError(
                f"Dérivation de plus de {self.settings.max_depth} étapes (max_depth) : "
                "récursion infinie probable, ou structure trop longue pour la limite configurée."
            )
        current, rest = goals[0], goals[1:]
        term = subst.walk(current.term)
        if isinstance(term, Var):
            raise InstantiationError("But non instancié (variable libre appelée).")
        if not isinstance(term, Struct | Atom):
            raise ExecutionError(f"But non appelable : {render(term)}.")
        goal = Goal(term, current.barrier, current.level)
        if term == TRUE:
            yield from self._solve(rest, subst, degree, depth + 1, steps, trace)
            return
        if term == FAIL or term == Atom("false"):
            return
        if term == CUT:
            for item in self._solve(rest, subst, degree, depth + 1, steps, trace):
                yield item
                if isinstance(item, _CutDone):
                    return
            yield _CutDone(goal.barrier)
            return
        if isinstance(term, Struct):
            handler = _CONTROL.get(term.indicator)
            if handler is not None:
                yield from handler(self, goal, rest, subst, degree, depth, steps, trace)
                return
            if term.functor == "call" and term.arity >= 1:
                yield from self._call(goal, rest, subst, degree, depth, steps, trace)
                return
        indicator = indicator_of(term)
        builtin = self.builtins.get(indicator)
        if builtin is not None:
            yield from self._builtin(
                builtin, indicator, goal, rest, subst, degree, depth, steps, trace
            )
            return
        yield from self._resolve(goal, rest, subst, degree, depth, steps, trace)

    def _builtin(
        self,
        builtin: Builtin,
        indicator: str,
        goal: Goal,
        rest: Goals,
        subst: Substitution,
        degree: float,
        depth: int,
        steps: Trace,
        trace: bool,
    ) -> Iterator[_Item]:
        args = goal.term.args if isinstance(goal.term, Struct) else ()
        for new_subst, own_degree in builtin(self, args, subst, degree):
            combined = self._combine(degree, own_degree)
            if combined is None:
                continue
            new_steps = self._record(
                steps, trace, goal, new_subst, f"prédéfini {indicator}", own_degree, combined
            )
            for item in self._solve(rest, new_subst, combined, depth + 1, new_steps, trace):
                yield item
                if isinstance(item, _CutDone):
                    return

    def _resolve(
        self,
        goal: Goal,
        rest: Goals,
        subst: Substitution,
        degree: float,
        depth: int,
        steps: Trace,
        trace: bool,
    ) -> Iterator[_Item]:
        """Resolution with the program clauses (course: *Résolution*, *Raisonnement en Prolog*)."""
        indicator = indicator_of(goal.term)
        if not self.program.defines(indicator):
            raise ExecutionError(f"Prédicat inconnu : {indicator}.")
        barrier = self._new_barrier()
        for clause in self.program.candidates(goal.term, subst):
            renamed = clause.rename(self._renamer)  # θ : renaming substitution
            unifier = unify(  # σ : most general unifier (with similarities)
                goal.term,
                renamed.head,
                subst,
                self.program.similarity,
                self.settings.tnorm,
                self.settings.occurs_check,
                self.settings.lambda_cut,
            )
            if unifier is None:
                continue
            step_degree = self.settings.tnorm(unifier.degree, clause.degree)
            combined = self._combine(degree, step_degree)
            if combined is None:
                continue
            new_steps = self._record(
                steps,
                trace,
                goal,
                unifier.substitution,
                clause_label(clause),
                step_degree,
                combined,
                unifier.similarities,
            )
            body: Goals = tuple(Goal(g, barrier, goal.level + 1) for g in renamed.body)
            for item in self._solve(
                body + rest, unifier.substitution, combined, depth + 1, new_steps, trace
            ):
                if isinstance(item, _CutDone):
                    if item.barrier != barrier:
                        yield item  # an outer cut: propagate upwards
                    return
                yield item

    def _call(
        self,
        goal: Goal,
        rest: Goals,
        subst: Substitution,
        degree: float,
        depth: int,
        steps: Trace,
        trace: bool,
    ) -> Iterator[_Item]:
        assert isinstance(goal.term, Struct)
        target = subst.walk(goal.term.args[0])
        extra = goal.term.args[1:]
        if extra:
            if isinstance(target, Atom):
                target = Struct(target.name, extra)
            elif isinstance(target, Struct):
                target = Struct(target.functor, target.args + extra)
            else:
                raise ExecutionError(f"call/{goal.term.arity} : but invalide {render(target)}.")
        barrier = self._new_barrier()  # call/N is opaque to cut
        inner = Goal(target, barrier, goal.level)
        for item in self._solve((inner, *rest), subst, degree, depth + 1, steps, trace):
            if isinstance(item, _CutDone):
                if item.barrier != barrier:
                    yield item
                return
            yield item


def clause_label(clause: Clause) -> str:
    """How a clause is named in proofs: its source line, or "fait" for programmatic facts."""
    return f"clause l.{clause.line} : {clause}" if clause.line else f"fait : {clause}"


# --- control constructs ---------------------------------------------------------------------

ControlHandler = Callable[
    [Engine, Goal, Goals, Substitution, float, int, Trace, bool],
    Iterator[_Item],
]


def _args(goal: Goal) -> tuple[Term, ...]:
    assert isinstance(goal.term, Struct)
    return goal.term.args


def _conjunction(
    engine: Engine,
    goal: Goal,
    rest: Goals,
    subst: Substitution,
    degree: float,
    depth: int,
    steps: Trace,
    trace: bool,
) -> Iterator[_Item]:
    left, right = _args(goal)
    goals = (Goal(left, goal.barrier, goal.level), Goal(right, goal.barrier, goal.level), *rest)
    yield from engine._solve(goals, subst, degree, depth, steps, trace)


def _disjunction(
    engine: Engine,
    goal: Goal,
    rest: Goals,
    subst: Substitution,
    degree: float,
    depth: int,
    steps: Trace,
    trace: bool,
) -> Iterator[_Item]:
    left, right = _args(goal)
    left = subst.walk(left)
    if isinstance(left, Struct) and left.indicator == "->/2":
        yield from _if_then_else(
            engine,
            left.args[0],
            left.args[1],
            right,
            goal,
            rest,
            subst,
            degree,
            depth,
            steps,
            trace,
        )
        return
    for item in engine._solve(
        (Goal(left, goal.barrier, goal.level), *rest), subst, degree, depth, steps, trace
    ):
        yield item
        if isinstance(item, _CutDone):
            return
    yield from engine._solve(
        (Goal(right, goal.barrier, goal.level), *rest), subst, degree, depth, steps, trace
    )


def _if_then(
    engine: Engine,
    goal: Goal,
    rest: Goals,
    subst: Substitution,
    degree: float,
    depth: int,
    steps: Trace,
    trace: bool,
) -> Iterator[_Item]:
    condition, then = _args(goal)
    yield from _if_then_else(
        engine, condition, then, FAIL, goal, rest, subst, degree, depth, steps, trace
    )


def _if_then_else(
    engine: Engine,
    condition: Term,
    then: Term,
    otherwise: Term,
    goal: Goal,
    rest: Goals,
    subst: Substitution,
    degree: float,
    depth: int,
    steps: Trace,
    trace: bool,
) -> Iterator[_Item]:
    local = engine._new_barrier()
    first: _Answer | None = None
    for item in engine._solve(
        (Goal(condition, local, goal.level + 1),), subst, degree, depth + 1, steps, trace
    ):
        if isinstance(item, _Answer):
            first = item
            break
    if first is None:
        branch = (Goal(otherwise, goal.barrier, goal.level), *rest)
        yield from engine._solve(branch, subst, degree, depth + 1, steps, trace)
        return
    branch = (Goal(then, goal.barrier, goal.level), *rest)
    yield from engine._solve(
        branch, first.substitution, first.degree, depth + 1, first.steps, trace
    )


def _negation(
    engine: Engine,
    goal: Goal,
    rest: Goals,
    subst: Substitution,
    degree: float,
    depth: int,
    steps: Trace,
    trace: bool,
) -> Iterator[_Item]:
    """``\\+ G`` : negation as failure, graded as ``1 − sup(degrees of G)``."""
    (inner,) = _args(goal)
    best = engine.best_degree(inner, subst)
    own = 1.0 - best
    combined = engine._combine(degree, own)
    if combined is None:
        return
    new_steps = engine._record(
        steps,
        trace,
        goal,
        subst,
        f"négation par l'échec (meilleur degré de G : {best:.2f})",
        own,
        combined,
    )
    for item in engine._solve(rest, subst, combined, depth + 1, new_steps, trace):
        yield item
        if isinstance(item, _CutDone):
            return


def _findall(
    engine: Engine,
    goal: Goal,
    rest: Goals,
    subst: Substitution,
    degree: float,
    depth: int,
    steps: Trace,
    trace: bool,
) -> Iterator[_Item]:
    """``findall(T, G, L)`` : instances of ``T`` (copied with fresh variables) for every
    solution of ``G``; the solutions' degrees are not kept (use ``with_degree/2``)."""
    template, inner, result = _args(goal)
    found = [
        engine._renamer.rename(s.resolve(template), {}) for s, _ in engine.solve_all(inner, subst)
    ]
    unifier = unify(result, make_list(found), subst, occurs_check=engine.settings.occurs_check)
    if unifier is None:
        return
    new_steps = engine._record(
        steps, trace, goal, unifier.substitution, f"findall ({len(found)} solutions)", 1.0, degree
    )
    for item in engine._solve(rest, unifier.substitution, degree, depth + 1, new_steps, trace):
        yield item
        if isinstance(item, _CutDone):
            return


_CONTROL: dict[str, ControlHandler] = {
    ",/2": _conjunction,
    ";/2": _disjunction,
    "->/2": _if_then,
    "\\+/1": _negation,
    "not/1": _negation,
    "findall/3": _findall,
}
