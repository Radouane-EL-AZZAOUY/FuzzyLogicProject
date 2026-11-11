"""The person record entity."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date


@dataclass(frozen=True, slots=True)
class DateValue:
    """A birth date as recorded: full date, year only, or unknown."""

    year: int | None = None
    month: int | None = None
    day: int | None = None

    @property
    def is_known(self) -> bool:
        return self.year is not None

    @property
    def is_full(self) -> bool:
        return self.year is not None and self.month is not None and self.day is not None

    @classmethod
    def parse(cls, text: str) -> DateValue:
        """``YYYY-MM-DD``, ``DD/MM/YYYY``, ``YYYY`` or empty (unknown)."""
        text = text.strip()
        if not text:
            return cls()
        if len(text) == 4 and text.isdigit():
            return cls(int(text))
        for pattern in ("%Y-%m-%d", "%d/%m/%Y", "%Y/%m/%d"):
            try:
                parsed = (
                    date.fromisoformat(text) if pattern == "%Y-%m-%d" else _strptime(text, pattern)
                )
            except ValueError:
                continue
            return cls(parsed.year, parsed.month, parsed.day)
        raise ValueError(f"date invalide : '{text}' (attendu AAAA-MM-JJ, JJ/MM/AAAA ou AAAA)")

    def __str__(self) -> str:
        if self.is_full:
            return f"{self.year:04d}-{self.month:02d}-{self.day:02d}"
        if self.year is not None:
            return f"{self.year:04d}"
        return "?"


def _strptime(text: str, pattern: str) -> date:
    from datetime import datetime

    return datetime.strptime(text, pattern).date()


@dataclass(frozen=True, slots=True)
class PersonRecord:
    identifier: str
    last_name: str
    first_name: str
    birth: DateValue = DateValue()
    city: str = ""
    phone: str = ""
    email: str = ""
    source: str = ""

    def __post_init__(self) -> None:
        if not self.identifier.strip():
            raise ValueError("Une fiche doit avoir un identifiant.")
        if not self.last_name.strip() and not self.first_name.strip():
            raise ValueError(f"La fiche '{self.identifier}' n'a ni nom ni prénom.")

    @property
    def full_name(self) -> str:
        return f"{self.first_name} {self.last_name}".strip()
