"""Exception hierarchy of the fuzzy engine.

Every error raised by the engine derives from :class:`FuzzyEngineError`, so callers
can catch a single type at the boundary of the library.
"""

from __future__ import annotations


class FuzzyEngineError(Exception):
    """Base class of all engine errors."""


class DefinitionError(FuzzyEngineError):
    """A membership function, universe or variable is ill-defined (invalid parameters)."""


class KnowledgeBaseError(FuzzyEngineError):
    """A rule base is inconsistent with its variables (unknown variable, unknown term...)."""


class ParseError(FuzzyEngineError):
    """The rule language text could not be parsed."""

    def __init__(self, message: str, line: int = 0, column: int = 0) -> None:
        location = f" (ligne {line}, colonne {column})" if line else ""
        super().__init__(f"{message}{location}")
        self.line = line
        self.column = column


class EvaluationError(FuzzyEngineError):
    """A system could not be evaluated (missing input value, unknown atom...)."""
