"""Universe of discourse of a linguistic variable (the domain *D* of the course)."""

from __future__ import annotations

from dataclasses import dataclass

from fuzzyengine.exceptions import DefinitionError


@dataclass(frozen=True, slots=True)
class Universe:
    """Closed real interval ``[lower, upper]`` on which a variable takes its values."""

    lower: float
    upper: float

    def __post_init__(self) -> None:
        if not self.lower < self.upper:
            raise DefinitionError(
                f"Univers invalide : la borne inférieure ({self.lower}) doit être "
                f"strictement inférieure à la borne supérieure ({self.upper})."
            )

    @property
    def width(self) -> float:
        return self.upper - self.lower

    @property
    def midpoint(self) -> float:
        return (self.lower + self.upper) / 2.0

    def contains(self, x: float) -> bool:
        return self.lower <= x <= self.upper

    def clamp(self, x: float) -> float:
        """Project ``x`` onto the universe (values outside are saturated at the bounds)."""
        return min(max(x, self.lower), self.upper)

    def grid(self, resolution: int) -> list[float]:
        """Return ``resolution`` evenly spaced sample points covering the universe."""
        if resolution < 2:
            raise DefinitionError("La résolution d'échantillonnage doit être >= 2.")
        step = self.width / (resolution - 1)
        return [self.lower + i * step for i in range(resolution)]
