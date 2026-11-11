"""CSV adapters.

Records file columns: ``id``, ``nom``, ``prenom`` (mandatory), ``date_naissance``
(``AAAA-MM-JJ``, ``JJ/MM/AAAA``, ``AAAA`` or empty), ``ville``, ``telephone``,
``email``, ``source`` (optional). Truth file columns: ``id``, ``personne``.
Delimiters ``,`` or ``;``; UTF-8 (with or without BOM) or Windows-1252.
"""

from __future__ import annotations

import csv
import io
from collections.abc import Mapping, Sequence
from pathlib import Path

from identitylink.domain.record import DateValue, PersonRecord

MANDATORY = ("id", "nom", "prenom")


class DataError(Exception):
    """A data file is unreadable or malformed."""


def _read_text(path: Path) -> str:
    try:
        data = path.read_bytes()
    except FileNotFoundError as exc:
        raise DataError(f"Fichier introuvable : {path}") from exc
    except OSError as exc:
        raise DataError(f"Impossible de lire {path} : {exc}") from exc
    for encoding in ("utf-8-sig", "cp1252"):
        try:
            return data.decode(encoding)
        except UnicodeDecodeError:
            continue
    raise DataError(f"{path} : encodage non reconnu.")


def _reader(text: str, path: Path) -> csv.DictReader[str]:
    if not text.strip():
        raise DataError(f"Fichier vide : {path}")
    header = text.splitlines()[0]
    delimiter = ";" if header.count(";") > header.count(",") else ","
    try:
        reader = csv.DictReader(io.StringIO(text), delimiter=delimiter)
        reader.fieldnames = [c.strip().casefold() for c in (reader.fieldnames or [])]
    except csv.Error as exc:
        raise DataError(f"{path} : CSV illisible ({exc}).") from exc
    return reader


def read_records(path: str | Path) -> list[PersonRecord]:
    file_path = Path(path)
    reader = _reader(_read_text(file_path), file_path)
    missing = [c for c in MANDATORY if c not in (reader.fieldnames or [])]
    if missing:
        raise DataError(
            f"{file_path} : colonne(s) obligatoire(s) absente(s) : {', '.join(missing)}."
        )
    records: list[PersonRecord] = []
    seen: set[str] = set()
    try:
        rows = list(reader)
    except csv.Error as exc:
        raise DataError(f"{file_path} : CSV illisible ({exc}).") from exc
    for number, row in enumerate(rows, start=2):
        identifier = (row.get("id") or "").strip()
        if not identifier:
            raise DataError(f"{file_path}, ligne {number} : identifiant vide.")
        if identifier in seen:
            raise DataError(f"{file_path}, ligne {number} : identifiant dupliqué '{identifier}'.")
        seen.add(identifier)
        try:
            records.append(
                PersonRecord(
                    identifier=identifier,
                    last_name=(row.get("nom") or "").strip(),
                    first_name=(row.get("prenom") or "").strip(),
                    birth=DateValue.parse(row.get("date_naissance") or ""),
                    city=(row.get("ville") or "").strip(),
                    phone=(row.get("telephone") or "").strip(),
                    email=(row.get("email") or "").strip(),
                    source=(row.get("source") or "").strip(),
                )
            )
        except ValueError as exc:
            raise DataError(f"{file_path}, ligne {number} : {exc}") from exc
    return records


def read_truth(path: str | Path) -> dict[str, str]:
    file_path = Path(path)
    reader = _reader(_read_text(file_path), file_path)
    if "id" not in (reader.fieldnames or []) or "personne" not in (reader.fieldnames or []):
        raise DataError(f"{file_path} : colonnes 'id' et 'personne' attendues.")
    truth: dict[str, str] = {}
    for number, row in enumerate(reader, start=2):
        identifier, person = (row.get("id") or "").strip(), (row.get("personne") or "").strip()
        if not identifier or not person:
            raise DataError(f"{file_path}, ligne {number} : valeur vide.")
        truth[identifier] = person
    return truth


class CsvRecordRepository:
    def __init__(self, path: str | Path) -> None:
        self._path = Path(path)
        self._records: list[PersonRecord] | None = None

    @property
    def path(self) -> Path:
        return self._path

    def all(self) -> Sequence[PersonRecord]:
        if self._records is None:
            self._records = read_records(self._path)
        return tuple(self._records)


class CsvTruth:
    def __init__(self, path: str | Path) -> None:
        self._path = Path(path)

    def person_of(self) -> Mapping[str, str]:
        return read_truth(self._path)
