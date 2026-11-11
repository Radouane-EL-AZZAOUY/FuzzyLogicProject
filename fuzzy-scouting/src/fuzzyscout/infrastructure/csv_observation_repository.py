"""Observations of the « commande Scout » system, read from a CSV file.

One row per player: an ``id`` column (the player's identifier in the players file)
and one column per observed variable. A cell holds a precise value (``4.12``), an
interval (``4.0..4.3`` or ``[4.0 ; 4.3]``) or a category (``court``); an empty cell
means *not observed*. Delimiters and encodings are those of the players file.
"""

from __future__ import annotations

import csv
import io
from collections.abc import Mapping
from pathlib import Path

from fuzzyengine import EvaluationError, Observation, parse_observation
from fuzzyscout.domain.errors import DataSourceError
from fuzzyscout.infrastructure.csv_player_repository import _detect_delimiter, _read_text

ID_COLUMN = "id"
IGNORED_COLUMNS = frozenset({ID_COLUMN, "nom", "club", "nationalite", "poste"})


def read_observations_csv(path: Path) -> dict[str, dict[str, Observation]]:
    text = _read_text(path)
    if not text.strip():
        raise DataSourceError(f"Fichier CSV vide : {path}")
    reader = csv.DictReader(io.StringIO(text), delimiter=_detect_delimiter(text.splitlines()[0]))
    reader.fieldnames = [c.strip() for c in (reader.fieldnames or [])]
    if ID_COLUMN not in reader.fieldnames:
        raise DataSourceError(f"{path} : colonne obligatoire absente : {ID_COLUMN}.")
    table: dict[str, dict[str, Observation]] = {}
    for row_number, row in enumerate(reader, start=2):
        identifier = (row.get(ID_COLUMN) or "").strip()
        if not identifier:
            raise DataSourceError(f"{path}, ligne {row_number} : colonne '{ID_COLUMN}' vide.")
        if identifier in table:
            raise DataSourceError(
                f"{path}, ligne {row_number} : identifiant dupliqué '{identifier}'."
            )
        observations: dict[str, Observation] = {}
        for column, raw in row.items():
            if column is None or column in IGNORED_COLUMNS or not (raw or "").strip():
                continue
            try:
                observations[column] = parse_observation(raw)
            except EvaluationError as exc:
                raise DataSourceError(
                    f"{path}, ligne {row_number}, colonne '{column}' : {exc}"
                ) from exc
        table[identifier] = observations
    return table


class CsvObservationRepository:
    """Lazy, read-once repository over a CSV file."""

    def __init__(self, path: str | Path) -> None:
        self._path = Path(path)
        self._table: dict[str, dict[str, Observation]] | None = None

    @property
    def path(self) -> Path:
        return self._path

    def for_player(self, identifier: str) -> Mapping[str, Observation]:
        if self._table is None:
            self._table = read_observations_csv(self._path)
        return self._table.get(identifier, {})


class NoObservations:
    """Used when no observation file is configured: players only have their statistics."""

    def for_player(self, identifier: str) -> Mapping[str, Observation]:
        return {}
