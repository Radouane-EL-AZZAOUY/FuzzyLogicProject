"""Crisp constraints applied before fuzzy scoring.

Hard constraints (budget, age limit, eligibility) are *filters*: a candidate either
satisfies them or not. Soft preferences are left to the fuzzy rules. Keeping the two
apart makes reports easy to read: a player is either *ranked* or *excluded for a
stated reason*.
"""

from __future__ import annotations

from dataclasses import dataclass

from fuzzyscout.domain.player import Player
from fuzzyscout.domain.position import Position


@dataclass(frozen=True, slots=True)
class RankingFilters:
    max_age: float | None = None
    max_market_value: float | None = None
    """Budget ceiling, in millions of euros."""
    min_minutes: float | None = None
    """Minimum playing time over the season (observability of the statistics)."""
    natural_position_only: bool = False
    nationality: str | None = None

    def rejection_reason(self, player: Player, position: Position) -> str | None:
        """Why ``player`` is excluded, or ``None`` when every constraint is satisfied."""
        if self.natural_position_only and player.position.casefold() != position.code.casefold():
            return f"poste naturel '{player.position or '?'}' différent de '{position.code}'"
        if self.nationality and player.nationality.upper() != self.nationality.upper():
            return f"nationalité '{player.nationality or '?'}' ≠ '{self.nationality}'"
        if self.max_age is not None:
            if player.age is None:
                return "âge inconnu (filtre d'âge actif)"
            if player.age > self.max_age:
                return f"âge {player.age:g} > {self.max_age:g}"
        if self.max_market_value is not None:
            if player.market_value is None:
                return "valeur marchande inconnue (filtre budget actif)"
            if player.market_value > self.max_market_value:
                return f"valeur {player.market_value:g} M€ > budget {self.max_market_value:g} M€"
        if self.min_minutes is not None:
            if player.minutes_played is None:
                return "temps de jeu inconnu (filtre de minutes actif)"
            if player.minutes_played < self.min_minutes:
                return f"temps de jeu {player.minutes_played:g} min < {self.min_minutes:g}"
        return None

    def describe(self) -> list[str]:
        parts: list[str] = []
        if self.natural_position_only:
            parts.append("poste naturel uniquement")
        if self.nationality:
            parts.append(f"nationalité = {self.nationality}")
        if self.max_age is not None:
            parts.append(f"âge ≤ {self.max_age:g}")
        if self.max_market_value is not None:
            parts.append(f"valeur ≤ {self.max_market_value:g} M€")
        if self.min_minutes is not None:
            parts.append(f"minutes ≥ {self.min_minutes:g}")
        return parts
