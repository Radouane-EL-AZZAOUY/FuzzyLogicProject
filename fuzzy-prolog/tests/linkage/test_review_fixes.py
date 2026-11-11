"""Regression tests for the application findings of the independent code review."""

from __future__ import annotations

from pathlib import Path

import pytest

from fuzzyprolog import String
from fuzzyprolog.tnorms import Product
from identitylink.application.deduplicate import Deduplicator, build_program
from identitylink.domain.normalization import name_forms, name_key, name_similarity
from identitylink.domain.record import DateValue, PersonRecord
from identitylink.infrastructure.csv_repository import DataError, read_records
from identitylink.infrastructure.knowledge import PackagedKnowledge

from .conftest import RECORDS


def test_cli_overrides_keep_the_rules_lambda_cut(knowledge: PackagedKnowledge) -> None:
    program = build_program(RECORDS, knowledge)
    assert Deduplicator(knowledge).settings_for(program).lambda_cut == pytest.approx(0.3)
    with_tnorm = Deduplicator(knowledge, tnorm=Product()).settings_for(program)
    assert with_tnorm.lambda_cut == pytest.approx(0.3) and with_tnorm.tnorm.name == "product"
    assert Deduplicator(knowledge, lambda_cut=0.5).settings_for(program).lambda_cut == 0.5


def test_record_ids_with_quotes_do_not_break_the_second_pass(deduplicator: Deduplicator) -> None:
    records = [
        PersonRecord("o'brien", "Tazi", "Sara", DateValue(2001, 9, 9), "Rabat", "0611111111"),
        PersonRecord("o'brien 2", "Tazy", "Sarah", DateValue(2001, 9, 9), "Rabat", "0611111111"),
    ]
    report = deduplicator.run(records, threshold=0.7)
    assert [c.pair for c in report.matches] == [("o'brien", "o'brien 2")]
    assert report.matches[0].proof.steps  # proof was re-derived despite the apostrophes


def test_geographic_proximity_is_not_a_similarity(knowledge: PackagedKnowledge) -> None:
    program = build_program(RECORDS, knowledge)
    assert program.similarity.degree(String("rabat"), String("sale")) == 0.0
    assert program.similarity.degree(String("casablanca"), String("casa")) == pytest.approx(0.95)


def test_consonant_skeleton_and_glued_particle_edge_cases() -> None:
    assert name_key("Nana") != name_key("Na")  # repeated consonants across vowels are kept
    assert name_key("Mohammed") == name_key("Mohamed")  # doubled consonant still reduced
    assert name_forms("Lotfi") == ["lotfi"]  # a single-letter particle needs 5 letters after it
    assert "amrani" in name_forms("Lamrani")
    assert name_similarity("Lotfi", "Otfi") < 1.0


def test_unreadable_csv_is_a_data_error(tmp_path: Path) -> None:
    path = tmp_path / "utf16.csv"
    path.write_bytes("id,nom,prenom\np1,A,B\n".encode("utf-16"))
    with pytest.raises(DataError):
        read_records(path)
