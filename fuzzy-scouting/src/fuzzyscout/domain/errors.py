"""Domain errors of the scouting application."""

from __future__ import annotations


class ScoutingError(Exception):
    """Base class of every scouting error (caught at the interface boundary)."""


class PlayerNotFoundError(ScoutingError):
    def __init__(self, identifier: str) -> None:
        super().__init__(f"Joueur inconnu : '{identifier}'.")
        self.identifier = identifier


class PositionNotFoundError(ScoutingError):
    def __init__(self, code: str, known: tuple[str, ...] = ()) -> None:
        hint = f" Postes connus : {', '.join(known)}." if known else ""
        super().__init__(f"Poste inconnu : '{code}'.{hint}")
        self.code = code


class MissingAttributesError(ScoutingError):
    def __init__(self, player_identifier: str, missing: tuple[str, ...]) -> None:
        super().__init__(
            f"Joueur '{player_identifier}' : attribut(s) manquant(s) : {', '.join(missing)}."
        )
        self.player_identifier = player_identifier
        self.missing = missing


class DataSourceError(ScoutingError):
    """A data file (CSV, TOML catalogue) is unreadable or malformed."""
