"""The Player entity."""

from __future__ import annotations

import math
from collections.abc import Iterable, Mapping
from dataclasses import dataclass, field
from types import MappingProxyType


@dataclass(frozen=True, slots=True)
class Player:
    """A candidate with identity data and a bag of measured attributes.

    ``attributes`` maps statistic names (the linguistic variable names used by the
    knowledge bases, e.g. ``buts_p90``) to their measured value. Only attributes that
    were actually measured are present; missing ones are simply absent. Values must
    be finite numbers (``NaN``/``inf`` are rejected rather than silently kept).
    """

    identifier: str
    name: str
    club: str = ""
    nationality: str = ""
    position: str = ""
    """Natural position code (e.g. ``attaquant``); may be empty."""
    attributes: Mapping[str, float] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.identifier.strip():
            raise ValueError("Un joueur doit avoir un identifiant.")
        if not self.name.strip():
            raise ValueError(f"Le joueur '{self.identifier}' doit avoir un nom.")
        clean: dict[str, float] = {}
        for key, raw in self.attributes.items():
            try:
                value = float(raw)
            except (TypeError, ValueError) as exc:
                raise ValueError(
                    f"Joueur '{self.identifier}' : attribut '{key}' non numérique ({raw!r})."
                ) from exc
            if not math.isfinite(value):
                raise ValueError(
                    f"Joueur '{self.identifier}' : attribut '{key}' non fini ({raw!r})."
                )
            clean[key] = value
        object.__setattr__(self, "attributes", MappingProxyType(clean))

    def attribute(self, name: str) -> float | None:
        return self.attributes.get(name)

    def missing(self, required: Iterable[str]) -> tuple[str, ...]:
        """Names from ``required`` that this player has no value for."""
        return tuple(name for name in required if name not in self.attributes)

    @property
    def age(self) -> float | None:
        return self.attribute("age")

    @property
    def market_value(self) -> float | None:
        return self.attribute("valeur_marche_meur")

    @property
    def minutes_played(self) -> float | None:
        return self.attribute("minutes_jouees")
