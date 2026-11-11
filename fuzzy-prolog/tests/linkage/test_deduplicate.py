from __future__ import annotations

import pytest

from identitylink.application.deduplicate import Deduplicator, build_program, record_facts
from identitylink.application.evaluate import evaluate, false_pairs, sweep, truth_pairs
from identitylink.domain.match import LinkageReport, cluster
from identitylink.infrastructure.csv_repository import read_records, read_truth
from identitylink.infrastructure.knowledge import PackagedKnowledge

from .conftest import RECORDS


def test_facts_built_for_a_record() -> None:
    facts = [str(f) for f in record_facts(RECORDS[0])]
    assert (
        facts[0]
        == 'fiche(p1, "El Amrani", "Mohamed", date(1990, 5, 12), "casablanca", "0612345678")'
    )
    assert any(f.startswith('bloc("nom:') and f.endswith(", p1)") for f in facts)
    assert 'bloc("tel:12345678", p1)' in facts


def test_program_contains_rules_similarities_and_facts(knowledge: PackagedKnowledge) -> None:
    program = build_program(RECORDS, knowledge)
    assert (
        program.defines("meme_personne/2")
        and program.defines("fiche/6")
        and program.defines("bloc/2")
    )
    assert program.settings.lambda_cut == pytest.approx(0.3)
    assert len(program.similarity) >= 10


def test_small_dataset_matches_and_explanations(small_report: LinkageReport) -> None:
    pairs = {c.pair: round(c.degree, 2) for c in small_report.matches}
    # Mohamed El Amrani : three records of the same person, matched through
    # name similarity + exact date (p1/p2), year-only date (p1/p3, p2/p3)
    assert pairs[("p1", "p2")] >= 0.9
    assert ("p1", "p3") in pairs and ("p2", "p3") in pairs
    # The namesake p4 (other birth date and city) is not matched with anyone
    assert not any("p4" in pair for pair in pairs)
    # Khadija Benjelloun : variants of both names, same date, city aliases Fes/Fez
    assert pairs[("p5", "p6")] >= 0.85
    assert not any("p7" in pair for pair in pairs)
    groups = [g.identifiers for g in small_report.groups]
    assert ("p1", "p2", "p3") in groups and ("p5", "p6") in groups
    best = next(c for c in small_report.matches if c.pair == ("p1", "p2"))
    text = best.proof.explain()
    assert "meme_personne" in best.rule and "clause l." in best.rule
    assert "nom_similaire" in text and "date_proche" in text


def test_threshold_validation(deduplicator: Deduplicator) -> None:
    with pytest.raises(ValueError):
        deduplicator.run(RECORDS, threshold=1.5)


def test_cluster_is_a_union_find() -> None:
    groups = cluster(RECORDS, [("p1", "p2"), ("p2", "p3"), ("p5", "p6")])
    assert [g.identifiers for g in groups] == [("p1", "p2", "p3"), ("p5", "p6")]
    assert cluster(RECORDS, []) == ()


def test_metrics_on_the_sample_dataset(
    deduplicator: Deduplicator, sample_paths: tuple[str, str]
) -> None:
    records = read_records(sample_paths[0])
    truth = truth_pairs(read_truth(sample_paths[1]))
    report = deduplicator.run(records, threshold=0.7)
    assert report.records == len(records) >= 200
    assert report.seconds < 60
    metrics = evaluate(report, truth)
    assert metrics.precision >= 0.95
    assert metrics.recall >= 0.80
    assert metrics.f1 >= 0.88
    curve = sweep(report, truth, (0.5, 0.7, 0.9))
    assert curve[0].recall >= curve[1].recall >= curve[2].recall
    assert curve[2].precision >= curve[0].precision
    fps, fns = false_pairs(report, truth)
    assert len(fps) <= 5 and len(fns) <= 25


def test_truth_pairs_enumerates_each_unordered_pair_once() -> None:
    pairs = truth_pairs({"a": "X", "b": "X", "c": "X", "d": "Y"})
    assert pairs == {("a", "b"), ("a", "c"), ("b", "c")}
    empty = evaluate(LinkageReport(0.7, ()), set())
    assert empty.precision == 1.0 and empty.recall == 1.0 and empty.f1 == 1.0
