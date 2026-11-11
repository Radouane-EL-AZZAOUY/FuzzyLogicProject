"""Exception hierarchy of the fuzzy logic-programming engine."""

from __future__ import annotations


class FuzzyPrologError(Exception):
    """Base class of every engine error."""


class ParseError(FuzzyPrologError):
    """The program or query text could not be parsed (line/column included)."""

    def __init__(self, message: str, line: int = 0, column: int = 0) -> None:
        location = f" (ligne {line}, colonne {column})" if line else ""
        super().__init__(f"{message}{location}")
        self.line = line
        self.column = column


class ProgramError(FuzzyPrologError):
    """A clause, directive or similarity declaration is ill-formed."""


class ExecutionError(FuzzyPrologError):
    """A goal could not be executed (unknown predicate, bad arithmetic, ...)."""


class InstantiationError(ExecutionError):
    """A built-in needed a bound argument but received a variable."""


class DepthLimitError(ExecutionError):
    """The resolution exceeded the configured depth (probable infinite recursion)."""
