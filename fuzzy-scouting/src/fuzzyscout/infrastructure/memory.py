"""In-memory adapters (tests, ad-hoc API usage)."""

from __future__ import annotations

from collections.abc import Iterable, Sequence

from fuzzyscout.domain.errors import PlayerNotFoundError, PositionNotFoundError
from fuzzyscout.domain.player import Player
from fuzzyscout.domain.position import Position


class InMemoryPlayerRepository:
    def __init__(self, players: Iterable[Player] = ()) -> None:
        self._players: dict[str, Player] = {}
        for player in players:
            self.add(player)

    def add(self, player: Player) -> None:
        if player.identifier in self._players:
            raise ValueError(f"Identifiant de joueur dupliqué : '{player.identifier}'.")
        self._players[player.identifier] = player

    def all(self) -> Sequence[Player]:
        return tuple(self._players.values())

    def get(self, identifier: str) -> Player:
        try:
            return self._players[identifier]
        except KeyError as exc:
            raise PlayerNotFoundError(identifier) from exc


class InMemoryPositionCatalog:
    def __init__(self, positions: Iterable[Position] = ()) -> None:
        self._positions: dict[str, Position] = {p.code: p for p in positions}

    def all(self) -> Sequence[Position]:
        return tuple(self._positions.values())

    def get(self, code: str) -> Position:
        try:
            return self._positions[code]
        except KeyError as exc:
            raise PositionNotFoundError(code, tuple(self._positions)) from exc
