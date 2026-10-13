"""Position catalogue read from ``positions.toml``.

::

    [[positions]]
    code = "attaquant"
    label = "Attaquant de pointe"
    description = "..."
    stages = ["technique/attaquant.toml", "physique/joueur_de_champ.toml", ...]
"""

from __future__ import annotations

import tomllib
from collections.abc import Sequence
from pathlib import Path
from typing import Any

from fuzzyscout.domain.errors import DataSourceError, PositionNotFoundError
from fuzzyscout.domain.position import Position


def parse_positions(document: dict[str, Any], source: str) -> list[Position]:
    entries = document.get("positions")
    if not isinstance(entries, list) or not entries:
        raise DataSourceError(f"{source} : la table [[positions]] est absente ou vide.")
    positions: list[Position] = []
    codes: set[str] = set()
    for index, entry in enumerate(entries):
        if not isinstance(entry, dict):
            raise DataSourceError(f"{source} : positions[{index}] doit être une table.")
        try:
            code = str(entry["code"])
            label = str(entry.get("label", code))
            stages = entry["stages"]
            if not isinstance(stages, list) or not all(isinstance(s, str) for s in stages):
                raise DataSourceError(
                    f"{source} : positions[{index}].stages doit être une liste de chemins."
                )
            position = Position(
                code=code,
                label=label,
                stages=tuple(stages),
                description=str(entry.get("description", "")),
            )
        except KeyError as exc:
            raise DataSourceError(
                f"{source} : positions[{index}] : clé obligatoire manquante {exc}."
            ) from exc
        except ValueError as exc:
            raise DataSourceError(f"{source} : positions[{index}] : {exc}") from exc
        if code in codes:
            raise DataSourceError(f"{source} : code de poste dupliqué '{code}'.")
        codes.add(code)
        positions.append(position)
    return positions


def read_positions(path: Path) -> list[Position]:
    try:
        document = tomllib.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise DataSourceError(f"Catalogue des postes introuvable : {path}") from exc
    except (OSError, UnicodeDecodeError) as exc:
        raise DataSourceError(f"Impossible de lire le catalogue des postes {path} : {exc}") from exc
    except tomllib.TOMLDecodeError as exc:
        raise DataSourceError(f"{path} : TOML invalide : {exc}") from exc
    return parse_positions(document, str(path))


class TomlPositionCatalog:
    def __init__(self, path: str | Path) -> None:
        self._path = Path(path)
        self._positions: dict[str, Position] | None = None

    def _load(self) -> dict[str, Position]:
        if self._positions is None:
            self._positions = {p.code: p for p in read_positions(self._path)}
        return self._positions

    def all(self) -> Sequence[Position]:
        return tuple(self._load().values())

    def get(self, code: str) -> Position:
        positions = self._load()
        try:
            return positions[code]
        except KeyError as exc:
            raise PositionNotFoundError(code, tuple(positions)) from exc
