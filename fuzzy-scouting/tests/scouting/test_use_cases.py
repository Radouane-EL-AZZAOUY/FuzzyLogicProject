from __future__ import annotations

import pytest

from fuzzyscout.application.rank_players import RankingRequest
from fuzzyscout.application.scouting_service import ScoutingService
from fuzzyscout.domain.errors import (
    MissingAttributesError,
    PlayerNotFoundError,
    PositionNotFoundError,
)
from fuzzyscout.domain.filters import RankingFilters


def test_evaluate_by_identifier_explains_itself(memory_service: ScoutingService) -> None:
    evaluation = memory_service.evaluate("attaquant", "S1")
    assert evaluation.aptitude > 70 and evaluation.aptitude_label in {"bonne", "excellente"}
    assert set(evaluation.scores) == {"technique", "physique", "profil", "aptitude"}
    strongest = evaluation.strongest_rules(limit=2)
    assert set(strongest) == {
        "technique_attaquant",
        "physique_joueur_de_champ",
        "profil_commun",
        "aptitude_commune",
    }
    assert strongest["technique_attaquant"][0].rule.identifier in {"T1", "T3"}
    assert evaluation.warnings == ()


def test_weak_candidate_scores_low(memory_service: ScoutingService) -> None:
    weak = memory_service.evaluate("attaquant", "S2")
    strong = memory_service.evaluate("attaquant", "S1")
    assert weak.aptitude < 40 < strong.aptitude
    assert weak.aptitude_label == "faible"


def test_evaluate_errors(memory_service: ScoutingService) -> None:
    with pytest.raises(PlayerNotFoundError):
        memory_service.evaluate("attaquant", "nobody")
    with pytest.raises(PositionNotFoundError):
        memory_service.evaluate("libero", "S1")
    with pytest.raises(MissingAttributesError) as info:
        memory_service.evaluate("attaquant", "S3")
    assert "buts_p90" in info.value.missing


def test_ad_hoc_evaluation(memory_service: ScoutingService, strong_striker) -> None:  # type: ignore[no-untyped-def]
    evaluation = memory_service.evaluate_attributes("attaquant", strong_striker.attributes, "Essai")
    assert evaluation.player.name == "Essai"
    assert evaluation.aptitude == pytest.approx(memory_service.evaluate("attaquant", "S1").aptitude)


def test_ranking_orders_filters_and_skips(memory_service: ScoutingService) -> None:
    report = memory_service.rank(RankingRequest("attaquant"))
    assert report.candidates == 3 and report.ranked == 2
    assert [e.evaluation.player.identifier for e in report.entries] == ["S1", "S2"]
    assert [e.rank for e in report.entries] == [1, 2]
    assert len(report.skipped) == 1 and "statistiques manquantes" in report.skipped[0].reason

    limited = memory_service.rank(RankingRequest("attaquant", limit=1))
    assert limited.ranked == 1

    filtered = memory_service.rank(
        RankingRequest("attaquant", RankingFilters(max_age=30, nationality="MA"))
    )
    assert [e.evaluation.player.identifier for e in filtered.entries] == ["S1"]
    reasons = {s.player.identifier: s.reason for s in filtered.skipped}
    assert "nationalité" in reasons["S2"]

    with pytest.raises(ValueError):
        RankingRequest("attaquant", limit=0)


def test_validate_knowledge_summarises_every_position(memory_service: ScoutingService) -> None:
    summaries = memory_service.validate_knowledge()
    assert {s.position.code for s in summaries} == {
        "gardien",
        "defenseur_central",
        "milieu_central",
        "ailier",
        "attaquant",
    }
    assert all(s.rules >= 40 for s in summaries)
    assert all("age" in s.required_inputs for s in summaries)


def test_sample_dataset_rankings_are_consistent(sample_service: ScoutingService) -> None:
    """On the synthetic dataset, natural-position players should dominate their own ranking."""
    for code in ("attaquant", "gardien", "milieu_central"):
        report = sample_service.rank(RankingRequest(code, limit=3))
        assert report.ranked == 3
        assert all(e.evaluation.player.position == code for e in report.entries[:1])
    goalkeepers = sample_service.rank(RankingRequest("gardien"))
    assert all(e.evaluation.player.position == "gardien" for e in goalkeepers.entries)
    assert len(goalkeepers.skipped) == len(sample_service.players()) - goalkeepers.ranked
