"""Built-in predicates.

A built-in is a function ``(engine, args, subst, degree) -> iterator of (subst, degree)``:
it may succeed zero, one or several times, each time with its *own* truth degree
(1 for crisp built-ins). Control constructs (``,`` ``;`` ``->`` ``\\+`` ``!`` ``call``
``findall``) are handled by the engine itself, not here.

Applications register their own graded built-ins with :func:`register` on a private
registry (see :class:`fuzzyprolog.engine.Engine`), which is the extension point used
by the identity-linkage application.
"""

from __future__ import annotations

import functools
import math
from collections.abc import Callable, Iterator
from typing import TYPE_CHECKING, Any

from fuzzyprolog.exceptions import ExecutionError, InstantiationError
from fuzzyprolog.substitution import Substitution
from fuzzyprolog.terms import (
    Atom,
    Number,
    String,
    Struct,
    Term,
    Var,
    is_constant,
    list_items,
    make_list,
    render,
)
from fuzzyprolog.textsim import jaro_winkler, normalize, text_similarity
from fuzzyprolog.unification import unify

if TYPE_CHECKING:
    from fuzzyprolog.engine import Engine

BuiltinResult = Iterator[tuple[Substitution, float]]
Builtin = Callable[["Engine", tuple[Term, ...], Substitution, float], BuiltinResult]

BUILTINS: dict[str, Builtin] = {}


def register(
    indicator: str, registry: dict[str, Builtin] | None = None
) -> Callable[[Builtin], Builtin]:
    """Decorator: register ``fn`` under ``name/arity`` (in the global registry by default)."""
    target = BUILTINS if registry is None else registry

    def decorator(fn: Builtin) -> Builtin:
        target[indicator] = fn
        return fn

    return decorator


def crisp(subst: Substitution) -> BuiltinResult:
    yield subst, 1.0


def graded(subst: Substitution, degree: float) -> BuiltinResult:
    if degree > 0.0:
        yield subst, min(1.0, degree)


# --- arithmetic ---------------------------------------------------------------------

Numeric = int | float
_BINARY: dict[str, Callable[[Any, Any], Any]] = {
    "+": lambda a, b: a + b,
    "-": lambda a, b: a - b,
    "*": lambda a, b: a * b,
    "/": lambda a, b: a / b,
    "//": lambda a, b: int(a) // int(b),
    "mod": lambda a, b: int(a) % int(b),
    "min": min,
    "max": max,
    "**": lambda a, b: a**b,
    "^": lambda a, b: a**b,
}
_UNARY: dict[str, Callable[[Any], Any]] = {
    "-": lambda a: -a,
    "+": lambda a: a,
    "abs": abs,
    "sqrt": math.sqrt,
    "float": float,
    "integer": lambda a: round(a),
    "truncate": lambda a: int(a),
    "round": lambda a: round(a),
}


def _numeric(value: object) -> Numeric:
    if isinstance(value, bool) or not isinstance(value, int | float):
        raise ExecutionError(f"Résultat arithmétique invalide : {value!r}.")
    return value


def evaluate(term: Term, subst: Substitution) -> Numeric:
    """Value of an arithmetic expression (``is/2`` and comparisons)."""
    term = subst.walk(term)
    if isinstance(term, Number):
        return term.value
    if isinstance(term, Var):
        raise InstantiationError("Expression arithmétique non instanciée.")
    if isinstance(term, Struct):
        try:
            if term.arity == 2 and term.functor in _BINARY:
                return _numeric(
                    _BINARY[term.functor](
                        evaluate(term.args[0], subst), evaluate(term.args[1], subst)
                    )
                )
            if term.arity == 1 and term.functor in _UNARY:
                return _numeric(_UNARY[term.functor](evaluate(term.args[0], subst)))
        except ZeroDivisionError as exc:
            raise ExecutionError("Division par zéro.") from exc
        except (ValueError, OverflowError) as exc:
            raise ExecutionError(
                f"Expression arithmétique invalide : {render(term)} ({exc})."
            ) from exc
    if isinstance(term, Atom) and term.name == "pi":
        return math.pi
    raise ExecutionError(f"Expression arithmétique invalide : {render(term)}.")


def _compare_numbers(indicator: str, test: Callable[[float, float], bool]) -> None:
    def fn(
        engine: Engine, args: tuple[Term, ...], subst: Substitution, degree: float
    ) -> BuiltinResult:
        if test(evaluate(args[0], subst), evaluate(args[1], subst)):
            yield subst, 1.0

    BUILTINS[indicator] = fn


_compare_numbers("=:=/2", lambda a, b: a == b)
_compare_numbers("=\\=/2", lambda a, b: a != b)
_compare_numbers("</2", lambda a, b: a < b)
_compare_numbers(">/2", lambda a, b: a > b)
_compare_numbers("=</2", lambda a, b: a <= b)
_compare_numbers(">=/2", lambda a, b: a >= b)


@register("is/2")
def _is(
    engine: Engine, args: tuple[Term, ...], subst: Substitution, degree: float
) -> BuiltinResult:
    value = evaluate(args[1], subst)
    unifier = unify(args[0], Number(value), subst, occurs_check=engine.settings.occurs_check)
    if unifier is not None:
        yield unifier.substitution, 1.0


# --- unification and identity -------------------------------------------------------


@register("=/2")
def _unify(
    engine: Engine, args: tuple[Term, ...], subst: Substitution, degree: float
) -> BuiltinResult:
    unifier = unify(
        args[0],
        args[1],
        subst,
        engine.program.similarity,
        engine.settings.tnorm,
        engine.settings.occurs_check,
    )
    if unifier is not None:
        yield unifier.substitution, unifier.degree


@register("\\=/2")
def _not_unify(
    engine: Engine, args: tuple[Term, ...], subst: Substitution, degree: float
) -> BuiltinResult:
    unifier = unify(args[0], args[1], subst, engine.program.similarity, engine.settings.tnorm)
    if unifier is None:
        yield subst, 1.0


@register("==/2")
def _identical(
    engine: Engine, args: tuple[Term, ...], subst: Substitution, degree: float
) -> BuiltinResult:
    if subst.resolve(args[0]) == subst.resolve(args[1]):
        yield subst, 1.0


@register("\\==/2")
def _not_identical(
    engine: Engine, args: tuple[Term, ...], subst: Substitution, degree: float
) -> BuiltinResult:
    if subst.resolve(args[0]) != subst.resolve(args[1]):
        yield subst, 1.0


# --- standard order of terms ----------------------------------------------------------

_RANK = {Var: 0, Number: 1, Atom: 2, String: 3, Struct: 4}


def compare_terms(a: Term, b: Term, subst: Substitution) -> int:
    a, b = subst.resolve(a), subst.resolve(b)
    ra, rb = _RANK[type(a)], _RANK[type(b)]
    if ra != rb:
        return -1 if ra < rb else 1
    if isinstance(a, Var) and isinstance(b, Var):
        ka, kb = (a.name, a.index), (b.name, b.index)
        return -1 if ka < kb else (1 if ka > kb else 0)
    if isinstance(a, Number) and isinstance(b, Number):
        return -1 if a.value < b.value else (1 if a.value > b.value else 0)
    if isinstance(a, Atom) and isinstance(b, Atom):
        return -1 if a.name < b.name else (1 if a.name > b.name else 0)
    if isinstance(a, String) and isinstance(b, String):
        return -1 if a.value < b.value else (1 if a.value > b.value else 0)
    if isinstance(a, Struct) and isinstance(b, Struct):
        if a.arity != b.arity:
            return -1 if a.arity < b.arity else 1
        if a.functor != b.functor:
            return -1 if a.functor < b.functor else 1
        for x, y in zip(a.args, b.args, strict=True):
            c = compare_terms(x, y, subst)
            if c != 0:
                return c
        return 0
    return 0  # pragma: no cover - all cases above are exhaustive


def _order(indicator: str, test: Callable[[int], bool]) -> None:
    def fn(
        engine: Engine, args: tuple[Term, ...], subst: Substitution, degree: float
    ) -> BuiltinResult:
        if test(compare_terms(args[0], args[1], subst)):
            yield subst, 1.0

    BUILTINS[indicator] = fn


_order("@</2", lambda c: c < 0)
_order("@>/2", lambda c: c > 0)
_order("@=</2", lambda c: c <= 0)
_order("@>=/2", lambda c: c >= 0)


@register("compare/3")
def _compare(
    engine: Engine, args: tuple[Term, ...], subst: Substitution, degree: float
) -> BuiltinResult:
    c = compare_terms(args[1], args[2], subst)
    symbol = Atom("<" if c < 0 else (">" if c > 0 else "="))
    unifier = unify(args[0], symbol, subst)
    if unifier is not None:
        yield unifier.substitution, 1.0


# --- type checks ------------------------------------------------------------------------


def _type_check(indicator: str, test: Callable[[Term], bool]) -> None:
    def fn(
        engine: Engine, args: tuple[Term, ...], subst: Substitution, degree: float
    ) -> BuiltinResult:
        if test(subst.walk(args[0])):
            yield subst, 1.0

    BUILTINS[indicator] = fn


_type_check("var/1", lambda t: isinstance(t, Var))
_type_check("nonvar/1", lambda t: not isinstance(t, Var))
_type_check("atom/1", lambda t: isinstance(t, Atom))
_type_check("number/1", lambda t: isinstance(t, Number))
_type_check("string/1", lambda t: isinstance(t, String))
_type_check("atomic/1", is_constant)
_type_check("compound/1", lambda t: isinstance(t, Struct))
_type_check("is_list/1", lambda t: list_items(t) is not None)


# --- text ----------------------------------------------------------------------------------


def text_of(term: Term, subst: Substitution, what: str) -> str:
    term = subst.walk(term)
    if isinstance(term, String):
        return term.value
    if isinstance(term, Atom):
        return term.name
    if isinstance(term, Number):
        return str(term.value)
    if isinstance(term, Var):
        raise InstantiationError(f"{what} : argument non instancié.")
    raise ExecutionError(f"{what} : texte attendu, reçu {render(term)}.")


@register("string_lower/2")
def _string_lower(
    engine: Engine, args: tuple[Term, ...], subst: Substitution, degree: float
) -> BuiltinResult:
    unifier = unify(args[1], String(text_of(args[0], subst, "string_lower/2").lower()), subst)
    if unifier is not None:
        yield unifier.substitution, 1.0


@register("string_length/2")
def _string_length(
    engine: Engine, args: tuple[Term, ...], subst: Substitution, degree: float
) -> BuiltinResult:
    unifier = unify(args[1], Number(len(text_of(args[0], subst, "string_length/2"))), subst)
    if unifier is not None:
        yield unifier.substitution, 1.0


@register("string_concat/3")
def _string_concat(
    engine: Engine, args: tuple[Term, ...], subst: Substitution, degree: float
) -> BuiltinResult:
    text = text_of(args[0], subst, "string_concat/3") + text_of(args[1], subst, "string_concat/3")
    unifier = unify(args[2], String(text), subst)
    if unifier is not None:
        yield unifier.substitution, 1.0


@register("atom_string/2")
def _atom_string(
    engine: Engine, args: tuple[Term, ...], subst: Substitution, degree: float
) -> BuiltinResult:
    first = subst.walk(args[0])
    if isinstance(first, Var):
        unifier = unify(first, Atom(text_of(args[1], subst, "atom_string/2")), subst)
    else:
        unifier = unify(args[1], String(text_of(first, subst, "atom_string/2")), subst)
    if unifier is not None:
        yield unifier.substitution, 1.0


# --- graded (fuzzy) built-ins ------------------------------------------------------------


@register("similar/3")
def _similar(
    engine: Engine, args: tuple[Term, ...], subst: Substitution, degree: float
) -> BuiltinResult:
    """``similar(A, B, D)`` : D is the declared similarity degree (0 when unrelated)."""
    a, b = subst.walk(args[0]), subst.walk(args[1])
    if isinstance(a, Var) or isinstance(b, Var):
        raise InstantiationError("similar/3 : les deux premiers arguments doivent être instanciés.")
    unifier = unify(args[2], Number(engine.program.similarity.degree(a, b)), subst)
    if unifier is not None:
        yield unifier.substitution, 1.0


@register("text_similar/2")
def _text_similar(
    engine: Engine, args: tuple[Term, ...], subst: Substitution, degree: float
) -> BuiltinResult:
    """Succeeds with the Jaro-Winkler similarity of the two normalised texts as degree."""
    a = text_of(args[0], subst, "text_similar/2")
    b = text_of(args[1], subst, "text_similar/2")
    yield from graded(subst, text_similarity(a, b))


@register("jaro_winkler/3")
def _jaro_winkler(
    engine: Engine, args: tuple[Term, ...], subst: Substitution, degree: float
) -> BuiltinResult:
    a = normalize(text_of(args[0], subst, "jaro_winkler/3"))
    b = normalize(text_of(args[1], subst, "jaro_winkler/3"))
    unifier = unify(args[2], Number(round(jaro_winkler(a, b), 4)), subst)
    if unifier is not None:
        yield unifier.substitution, 1.0


@register("number_close/3")
def _number_close(
    engine: Engine, args: tuple[Term, ...], subst: Substitution, degree: float
) -> BuiltinResult:
    """``number_close(X, Y, Tol)`` : degree ``1 - |X - Y| / Tol`` (0 beyond the tolerance)."""
    x, y, tolerance = (evaluate(a, subst) for a in args)
    if tolerance <= 0:
        raise ExecutionError("number_close/3 : la tolérance doit être > 0.")
    yield from graded(subst, 1.0 - abs(x - y) / tolerance)


@register("with_degree/2")
def _with_degree(
    engine: Engine, args: tuple[Term, ...], subst: Substitution, degree: float
) -> BuiltinResult:
    """``with_degree(Goal, D)`` : solutions of Goal, with D bound to their degree."""
    goal = subst.walk(args[0])
    for solution_subst, solution_degree in engine.solve_all(goal, subst):
        unifier = unify(args[1], Number(round(solution_degree, 6)), solution_subst)
        if unifier is not None:
            yield unifier.substitution, solution_degree


@register("best_degree/2")
def _best_degree(
    engine: Engine, args: tuple[Term, ...], subst: Substitution, degree: float
) -> BuiltinResult:
    """``best_degree(Goal, D)`` : D is the highest degree of any solution of Goal (0 if none)."""
    best = engine.best_degree(subst.walk(args[0]), subst)
    unifier = unify(args[1], Number(round(best, 6)), subst)
    if unifier is not None:
        yield unifier.substitution, 1.0


# --- lists (deterministic helpers) ---------------------------------------------------------


@register("msort/2")
def _msort(
    engine: Engine, args: tuple[Term, ...], subst: Substitution, degree: float
) -> BuiltinResult:
    items = list_items(subst.resolve(args[0]))
    if items is None:
        raise ExecutionError("msort/2 : liste attendue.")

    def compare(a: Term, b: Term) -> int:
        return compare_terms(a, b, subst)

    ordered = sorted(items, key=functools.cmp_to_key(compare))
    unifier = unify(args[1], make_list(ordered), subst)
    if unifier is not None:
        yield unifier.substitution, 1.0


# --- output ---------------------------------------------------------------------------------


@register("write/1")
def _write(
    engine: Engine, args: tuple[Term, ...], subst: Substitution, degree: float
) -> BuiltinResult:
    term = subst.resolve(args[0])
    engine.output(term.value if isinstance(term, String) else render(term))
    yield subst, 1.0


@register("writeln/1")
def _writeln(
    engine: Engine, args: tuple[Term, ...], subst: Substitution, degree: float
) -> BuiltinResult:
    term = subst.resolve(args[0])
    engine.output((term.value if isinstance(term, String) else render(term)) + "\n")
    yield subst, 1.0


@register("nl/0")
def _nl(
    engine: Engine, args: tuple[Term, ...], subst: Substitution, degree: float
) -> BuiltinResult:
    engine.output("\n")
    yield subst, 1.0
