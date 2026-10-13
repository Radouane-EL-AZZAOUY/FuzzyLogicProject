import pytest

from fuzzyscout.domain.filters import RankingFilters
from fuzzyscout.domain.player import Player
from fuzzyscout.domain.position import Position


def test_player_attributes_are_frozen_floats() -> None:
    player = Player("P1", "Nom", attributes={"age": 24, "buts_p90": "0.5"})  # type: ignore[dict-item]
    assert player.age == 24.0 and player.attribute("buts_p90") == 0.5
    assert player.attribute("inconnu") is None
    assert player.missing(["age", "xg_p90", "buts_p90"]) == ("xg_p90",)
    with pytest.raises(TypeError):
        player.attributes["age"] = 30  # type: ignore[index]


def test_player_and_position_invariants() -> None:
    with pytest.raises(ValueError):
        Player(" ", "Nom")
    with pytest.raises(ValueError):
        Player("P1", "")
    with pytest.raises(ValueError):
        Position("", "x", ("a.toml",))
    with pytest.raises(ValueError):
        Position("att", "x", ())


def test_filters_rejection_reasons() -> None:
    position = Position("attaquant", "Attaquant", ("a.toml",))
    player = Player(
        "P1",
        "Nom",
        nationality="MA",
        position="ailier",
        attributes={"age": 27, "valeur_marche_meur": 9.5, "minutes_jouees": 1200},
    )
    assert RankingFilters().rejection_reason(player, position) is None
    assert "poste naturel" in (
        RankingFilters(natural_position_only=True).rejection_reason(player, position) or ""
    )
    assert RankingFilters(nationality="ma").rejection_reason(player, position) is None
    assert "nationalité" in (
        RankingFilters(nationality="FR").rejection_reason(player, position) or ""
    )
    assert "âge" in (RankingFilters(max_age=25).rejection_reason(player, position) or "")
    assert "budget" in (RankingFilters(max_market_value=5).rejection_reason(player, position) or "")
    assert "temps de jeu" in (
        RankingFilters(min_minutes=1500).rejection_reason(player, position) or ""
    )
    unknown = Player("P2", "Inconnu")
    assert "inconnu" in (RankingFilters(max_age=25).rejection_reason(unknown, position) or "")
    assert "inconnue" in (
        RankingFilters(max_market_value=5).rejection_reason(unknown, position) or ""
    )
    assert "inconnu" in (RankingFilters(min_minutes=5).rejection_reason(unknown, position) or "")


def test_filters_description() -> None:
    filters = RankingFilters(
        max_age=25,
        max_market_value=10,
        min_minutes=900,
        natural_position_only=True,
        nationality="MA",
    )
    text = " ; ".join(filters.describe())
    assert "âge ≤ 25" in text and "valeur ≤ 10" in text and "minutes ≥ 900" in text
    assert "poste naturel" in text and "nationalité = MA" in text
    assert RankingFilters().describe() == []
