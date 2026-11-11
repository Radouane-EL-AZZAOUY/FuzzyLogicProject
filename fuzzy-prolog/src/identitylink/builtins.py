"""Graded built-ins contributed by the application to the fuzzy Prolog engine.

They expose the domain's normalisation functions to the rules as predicates that
*succeed with a degree* — the extension mechanism of ``fuzzyprolog`` (no change to
the engine is needed to add a domain).
"""

from __future__ import annotations

from fuzzyprolog import Atom, Builtin, Engine, Number, Struct, Substitution, Term, Var
from fuzzyprolog.builtins import BuiltinResult, graded, register, text_of
from fuzzyprolog.exceptions import ExecutionError, InstantiationError
from identitylink.domain.normalization import date_similarity, name_similarity, phone_similarity
from identitylink.domain.record import DateValue

LINKAGE_BUILTINS: dict[str, Builtin] = {}


def date_term(value: DateValue) -> Term:
    """``date(Y, M, D)``, ``annee(Y)`` or ``inconnue``."""
    if value.is_full:
        return Struct("date", (Number(value.year), Number(value.month), Number(value.day)))  # type: ignore[arg-type]
    if value.year is not None:
        return Struct("annee", (Number(value.year),))
    return Atom("inconnue")


def date_value(term: Term, subst: Substitution) -> DateValue:
    term = subst.resolve(term)
    if isinstance(term, Struct) and term.functor == "date" and term.arity == 3:
        y, m, d = term.args
        if isinstance(y, Number) and isinstance(m, Number) and isinstance(d, Number):
            return DateValue(int(y.value), int(m.value), int(d.value))
    if isinstance(term, Struct) and term.functor == "annee" and term.arity == 1:
        y = term.args[0]
        if isinstance(y, Number):
            return DateValue(int(y.value))
    if term == Atom("inconnue"):
        return DateValue()
    if isinstance(term, Var):
        raise InstantiationError("date : argument non instancié.")
    raise ExecutionError("date : terme date(A, M, J), annee(A) ou inconnue attendu.")


@register("nom_similaire/2", LINKAGE_BUILTINS)
def _nom_similaire(
    engine: Engine, args: tuple[Term, ...], subst: Substitution, degree: float
) -> BuiltinResult:
    """Degree = transliteration-aware similarity of two names (fails below the floor)."""
    yield from graded(
        subst,
        name_similarity(
            text_of(args[0], subst, "nom_similaire/2"), text_of(args[1], subst, "nom_similaire/2")
        ),
    )


@register("date_proche/2", LINKAGE_BUILTINS)
def _date_proche(
    engine: Engine, args: tuple[Term, ...], subst: Substitution, degree: float
) -> BuiltinResult:
    yield from graded(
        subst, date_similarity(date_value(args[0], subst), date_value(args[1], subst))
    )


@register("date_connue/1", LINKAGE_BUILTINS)
def _date_connue(
    engine: Engine, args: tuple[Term, ...], subst: Substitution, degree: float
) -> BuiltinResult:
    if date_value(args[0], subst).is_known:
        yield subst, 1.0


@register("tel_similaire/2", LINKAGE_BUILTINS)
def _tel_similaire(
    engine: Engine, args: tuple[Term, ...], subst: Substitution, degree: float
) -> BuiltinResult:
    yield from graded(
        subst,
        phone_similarity(
            text_of(args[0], subst, "tel_similaire/2"), text_of(args[1], subst, "tel_similaire/2")
        ),
    )
