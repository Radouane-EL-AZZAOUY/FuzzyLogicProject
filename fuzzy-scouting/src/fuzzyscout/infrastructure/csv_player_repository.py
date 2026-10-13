"""Player repository backed by a CSV file.

Expected columns: ``id``, ``nom`` (mandatory), ``club``, ``nationalite``, ``poste``
(optional) and any number of numeric statistic columns. Empty cells mean *not
measured*. Both ``,`` and ``;`` delimiters are accepted (Excel exports), as well
as a UTF-8 byte-order mark, decimal commas and, as a fallback, the Windows-1252
encoding used by Excel's default CSV export.
"""

from __future__ import annotations

import csv
import io
import logging
import math
from collections.abc import Iterable, Mapping, Sequence
from pathlib import Path

from fuzzyscout.domain.errors import DataSourceError, PlayerNotFoundError
from fuzzyscout.domain.player import Player

logger = logging.getLogger(__name__)

IDENTITY_COLUMNS: tuple[str, ...] = ("id", "nom", "club", "nationalite", "poste")
MANDATORY_COLUMNS: tuple[str, ...] = ("id", "nom")
ENCODINGS: tuple[str, ...] = ("utf-8-sig", "cp1252")


def _to_float(raw: str, row_number: int, column: str) -> float | None:
    text = raw.strip().replace(",", ".")
    if not text:
        return None
    try:
        value = float(text)
    except ValueError as exc:
        raise DataSourceError(
            f"Ligne {row_number}, colonne '{column}' : valeur numérique invalide '{raw}'."
        ) from exc
    if not math.isfinite(value):
        raise DataSourceError(
            f"Ligne {row_number}, colonne '{column}' : valeur non finie '{raw}' "
            "(laisser la cellule vide pour « non mesuré »)."
        )
    return value


def parse_players(rows: Iterable[Mapping[str, str]], start_row: int = 2) -> list[Player]:
    """Turn CSV rows (dicts) into players; shared by the file and in-memory paths."""
    players: list[Player] = []
    seen: set[str] = set()
    for offset, row in enumerate(rows):
        row_number = start_row + offset
        for column in MANDATORY_COLUMNS:
            if not (row.get(column) or "").strip():
                raise DataSourceError(f"Ligne {row_number} : colonne obligatoire '{column}' vide.")
        identifier = row["id"].strip()
        if identifier in seen:
            raise DataSourceError(f"Ligne {row_number} : identifiant dupliqué '{identifier}'.")
        seen.add(identifier)
        attributes: dict[str, float] = {}
        for column, raw in row.items():
            if column is None or column in IDENTITY_COLUMNS:
                continue
            value = _to_float(raw or "", row_number, column)
            if value is not None:
                attributes[column.strip()] = value
        players.append(
            Player(
                identifier=identifier,
                name=row["nom"].strip(),
                club=(row.get("club") or "").strip(),
                nationality=(row.get("nationalite") or "").strip(),
                position=(row.get("poste") or "").strip(),
                attributes=attributes,
            )
        )
    return players


def _detect_delimiter(header_line: str) -> str:
    return ";" if header_line.count(";") > header_line.count(",") else ","


def _read_text(path: Path) -> str:
    try:
        data = path.read_bytes()
    except FileNotFoundError as exc:
        raise DataSourceError(f"Fichier de joueurs introuvable : {path}") from exc
    except OSError as exc:
        raise DataSourceError(f"Impossible de lire le fichier de joueurs {path} : {exc}") from exc
    for encoding in ENCODINGS:
        try:
            text = data.decode(encoding)
        except UnicodeDecodeError:
            continue
        if encoding != ENCODINGS[0]:
            logger.info("%s n'est pas en UTF-8 : lu en %s", path, encoding)
        return text
    raise DataSourceError(f"{path} : encodage non reconnu (attendu UTF-8 ou Windows-1252).")


def read_players_csv(path: Path) -> list[Player]:
    text = _read_text(path)
    if not text.strip():
        raise DataSourceError(f"Fichier CSV vide : {path}")
    header_line = text.splitlines()[0]
    reader = csv.DictReader(io.StringIO(text), delimiter=_detect_delimiter(header_line))
    columns = [c.strip() for c in (reader.fieldnames or [])]
    missing = [c for c in MANDATORY_COLUMNS if c not in columns]
    if missing:
        raise DataSourceError(
            f"{path} : colonne(s) obligatoire(s) absente(s) : {', '.join(missing)}."
        )
    reader.fieldnames = columns
    try:
        return parse_players(reader)
    except ValueError as exc:  # raised by Player invariants
        raise DataSourceError(f"{path} : {exc}") from exc


class CsvPlayerRepository:
    """Lazy, read-once repository over a CSV file."""

    def __init__(self, path: str | Path) -> None:
        self._path = Path(path)
        self._players: dict[str, Player] | None = None

    @property
    def path(self) -> Path:
        return self._path

    def _load(self) -> dict[str, Player]:
        if self._players is None:
            self._players = {p.identifier: p for p in read_players_csv(self._path)}
        return self._players

    def all(self) -> Sequence[Player]:
        return tuple(self._load().values())

    def get(self, identifier: str) -> Player:
        try:
            return self._load()[identifier]
        except KeyError as exc:
            raise PlayerNotFoundError(identifier) from exc
