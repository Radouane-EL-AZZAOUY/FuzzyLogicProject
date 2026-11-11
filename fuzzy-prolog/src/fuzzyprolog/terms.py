"""Terms of the language, exactly as defined in the course (*Logique des prédicats*):

* a **constant** (:class:`Atom`, :class:`Number`, :class:`String`),
* a **variable** (:class:`Var`),
* a compound term ``f(t1, …, tn)`` (:class:`Struct`), where *f* is a function symbol.

An atomic formula ``P(t1, …, tn)`` is represented by a :class:`Struct` too (the course
notes that a predicate of arity 0 is a proposition: here a bare :class:`Atom`).
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import ClassVar


class Term:
    """Root of the term hierarchy (never instantiated directly)."""

    __slots__ = ()


@dataclass(frozen=True, slots=True)
class Var(Term):
    """A logic variable. ``index`` distinguishes fresh copies made when a clause is
    *renamed* before resolution (the θ of the course); ``0`` marks variables as written
    in the source text."""

    name: str
    index: int = 0

    def __str__(self) -> str:
        if self.name.startswith("_"):
            return "_"
        return self.name if self.index == 0 else f"{self.name}_{self.index}"


@dataclass(frozen=True, slots=True)
class Atom(Term):
    """A symbolic constant (``ali``, ``[]``, ``!``)."""

    name: str

    def __str__(self) -> str:
        return quote_atom(self.name)


@dataclass(frozen=True, slots=True)
class Number(Term):
    value: int | float

    def __str__(self) -> str:
        return str(self.value)


@dataclass(frozen=True, slots=True)
class String(Term):
    """A double-quoted text constant (names, cities...), distinct from atoms."""

    value: str

    def __str__(self) -> str:
        escaped = self.value.replace("\\", "\\\\").replace('"', '\\"')
        return f'"{escaped}"'


@dataclass(frozen=True, slots=True)
class Struct(Term):
    """``functor(args…)`` — both compound terms and atomic formulas."""

    functor: str
    args: tuple[Term, ...]

    LIST_FUNCTOR: ClassVar[str] = "."

    @property
    def arity(self) -> int:
        return len(self.args)

    @property
    def indicator(self) -> str:
        return f"{self.functor}/{self.arity}"

    def __str__(self) -> str:
        return render(self)


EMPTY_LIST = Atom("[]")
TRUE = Atom("true")
FAIL = Atom("fail")
CUT = Atom("!")

Constant = Atom | Number | String


def indicator_of(term: Term) -> str:
    """``name/arity`` of a callable term (atom = arity 0)."""
    if isinstance(term, Struct):
        return term.indicator
    if isinstance(term, Atom):
        return f"{term.name}/0"
    raise TypeError(f"Terme non appelable : {render(term)}")


def is_callable(term: Term) -> bool:
    return isinstance(term, Struct | Atom)


def is_constant(term: Term) -> bool:
    return isinstance(term, Atom | Number | String)


def make_list(items: list[Term] | tuple[Term, ...], tail: Term = EMPTY_LIST) -> Term:
    result = tail
    for item in reversed(items):
        result = Struct(Struct.LIST_FUNCTOR, (item, result))
    return result


def list_items(term: Term) -> list[Term] | None:
    """Elements of a proper list, or ``None`` if ``term`` is not a proper list."""
    items: list[Term] = []
    while True:
        if term == EMPTY_LIST:
            return items
        if isinstance(term, Struct) and term.functor == Struct.LIST_FUNCTOR and term.arity == 2:
            items.append(term.args[0])
            term = term.args[1]
            continue
        return None


# --- rendering ------------------------------------------------------------------

from fuzzyprolog.operators import (  # noqa: E402  (kept close to its only use)
    ARGUMENT_PRIORITY,
    INFIX,
    PREFIX,
    SPACED,
    argument_priorities,
)


def quote_atom(name: str) -> str:
    if not name:
        return "''"
    if name in {"[]", "!", ";", ",", "{}"}:
        return name
    if name[0].islower() and all(c.isalnum() or c == "_" for c in name):
        return name
    if all(c in r"+-*/\^<>=~:.?@#&$" for c in name):
        return name
    escaped = name.replace("\\", "\\\\").replace("'", "''")
    return f"'{escaped}'"


def render(term: Term, max_priority: int = 1200) -> str:
    """Prolog-style text of a term: lists, operators (with the minimal parentheses
    required by their priorities) and quoting are handled."""
    if not isinstance(term, Struct):
        return str(term)
    if term.functor == Struct.LIST_FUNCTOR and term.arity == 2:
        head, tail = _split_list(term)
        inner = ", ".join(render(i, ARGUMENT_PRIORITY) for i in head)
        if tail == EMPTY_LIST:
            return f"[{inner}]"
        return f"[{inner} | {render(tail, ARGUMENT_PRIORITY)}]"
    if term.arity == 2 and term.functor in INFIX:
        priority, kind = INFIX[term.functor]
        left_max, right_max = argument_priorities(priority, kind)
        left, right = render(term.args[0], left_max), render(term.args[1], right_max)
        if term.functor == ",":
            text = f"{left}, {right}"
        elif term.functor in SPACED:
            text = f"{left} {term.functor} {right}"
        else:
            text = f"{left}{term.functor}{right}"
        return f"({text})" if priority > max_priority else text
    if term.arity == 1 and term.functor in PREFIX:
        priority, kind = PREFIX[term.functor]
        operand_max = priority if kind == "fy" else priority - 1
        text = f"{term.functor} {render(term.args[0], operand_max)}"
        return f"({text})" if priority > max_priority else text
    args = ", ".join(render(a, ARGUMENT_PRIORITY) for a in term.args)
    return f"{quote_atom(term.functor)}({args})"


def _split_list(term: Term) -> tuple[list[Term], Term]:
    head: list[Term] = []
    while isinstance(term, Struct) and term.functor == Struct.LIST_FUNCTOR and term.arity == 2:
        head.append(term.args[0])
        term = term.args[1]
    return head, term
