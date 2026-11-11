"""Operator table shared by the parser and the term renderer (standard Prolog subset).

``INFIX`` and ``PREFIX`` map an operator name to ``(priority, type)`` where the type
follows the ISO convention: ``xfx`` / ``xfy`` / ``yfx`` for infix operators, ``fy`` / ``fx``
for prefix ones (``x`` = argument of strictly lower priority, ``y`` = same priority
allowed). Lower priority binds tighter.
"""

from __future__ import annotations

INFIX: dict[str, tuple[int, str]] = {
    ":-": (1200, "xfx"),
    "-->": (1200, "xfx"),
    ";": (1100, "xfy"),
    "->": (1050, "xfy"),
    ",": (1000, "xfy"),
    "=": (700, "xfx"),
    "\\=": (700, "xfx"),
    "==": (700, "xfx"),
    "\\==": (700, "xfx"),
    "@<": (700, "xfx"),
    "@>": (700, "xfx"),
    "@=<": (700, "xfx"),
    "@>=": (700, "xfx"),
    "is": (700, "xfx"),
    "=:=": (700, "xfx"),
    "=\\=": (700, "xfx"),
    "<": (700, "xfx"),
    ">": (700, "xfx"),
    "=<": (700, "xfx"),
    ">=": (700, "xfx"),
    "~": (700, "xfx"),
    "+": (500, "yfx"),
    "-": (500, "yfx"),
    "*": (400, "yfx"),
    "/": (400, "yfx"),
    "//": (400, "yfx"),
    "mod": (400, "yfx"),
    "**": (200, "xfx"),
    "^": (200, "xfy"),
}

PREFIX: dict[str, tuple[int, str]] = {
    ":-": (1200, "fx"),
    "\\+": (900, "fy"),
    "-": (200, "fy"),
    "+": (200, "fy"),
}

ARGUMENT_PRIORITY = 999
"""Maximum priority of a term used as an argument or a list element."""

SPACED = frozenset({":-", "-->", ";", "->", "is", "mod", "~", "**"}) | frozenset(
    name for name, (priority, _) in INFIX.items() if priority == 700
)
"""Operators rendered with surrounding spaces (the arithmetic ones are rendered tight)."""


def argument_priorities(priority: int, kind: str) -> tuple[int, int]:
    """Maximum priorities allowed for the left and right arguments of an infix operator."""
    left = priority if kind == "yfx" else priority - 1
    right = priority if kind == "xfy" else priority - 1
    return left, right
