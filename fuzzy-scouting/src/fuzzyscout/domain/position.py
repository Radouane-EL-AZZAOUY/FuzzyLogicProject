"""The Position value object."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class Position:
    """A playing position and the ordered knowledge bases evaluating it.

    ``stages`` lists knowledge-base files (relative to the knowledge directory) that
    are chained into a pipeline; the last stage must produce the final aptitude.
    """

    code: str
    label: str
    stages: tuple[str, ...]
    description: str = ""

    def __post_init__(self) -> None:
        if not self.code.strip():
            raise ValueError("Un poste doit avoir un code.")
        if not self.stages:
            raise ValueError(f"Le poste '{self.code}' doit déclarer au moins une étape.")
