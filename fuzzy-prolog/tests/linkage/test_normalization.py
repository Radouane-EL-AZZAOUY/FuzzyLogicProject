import pytest

from identitylink.domain.normalization import (
    blocking_keys,
    date_similarity,
    name_key,
    name_similarity,
    normalize_phone,
    phone_similarity,
)
from identitylink.domain.record import DateValue, PersonRecord


@pytest.mark.parametrize(
    ("a", "b"),
    [
        ("Mohamed", "Mohammed"),
        ("Mohamed", "Muhammad"),
        ("El Amrani", "Lamrani"),
        ("Fatima Zahra", "Fatima-Zohra"),
        ("Youssef", "Yusuf"),
        ("Benjelloun", "Ben Jelloun"),
        ("Ait Ali", "Aitali"),
        ("Chraïbi", "Chraibi"),
    ],
)
def test_transliteration_variants_share_a_key_or_are_very_similar(a: str, b: str) -> None:
    assert name_key(a) == name_key(b) or name_similarity(a, b) >= 0.85


def test_name_key_examples() -> None:
    assert name_key("Mohamed") == name_key("Mohammed") == name_key("Muhammad") == "mmhmd"
    assert name_key("El Amrani") == name_key("Amrani")
    assert name_key("Ahmed") != name_key("Hamid")  # first letter kept on purpose
    assert name_key("Lamrani") == name_key("El Amrani") == name_key("Amrani")
    assert name_key("Benjelloun") == name_key("Ben Jelloun")
    assert name_key("") == ""


def test_name_similarity_bounds_and_floor() -> None:
    assert name_similarity("Tazi", "Tazi") == 1.0
    assert name_similarity("Tazi", "TAZI ") == 1.0
    assert name_similarity("Tazi", "Benjelloun") == 0.0  # below the floor
    assert 0.6 <= name_similarity("Hassan", "Hasan") <= 1.0
    assert name_similarity("", "x") == 0.0


def test_date_similarity_grades() -> None:
    full = DateValue(1990, 5, 12)
    assert date_similarity(full, DateValue(1990, 5, 12)) == 1.0
    assert date_similarity(full, DateValue(1990, 5, 14)) == 0.85
    assert date_similarity(full, DateValue(1990, 12, 5)) == 0.75
    assert date_similarity(full, DateValue(1991, 5, 12)) == 0.7
    assert date_similarity(full, DateValue(1990, 1, 1)) == 0.4
    assert date_similarity(full, DateValue(1985, 5, 12)) == 0.0
    assert date_similarity(full, DateValue(1990)) == 0.7
    assert date_similarity(DateValue(1990), DateValue(1990)) == 0.6
    assert date_similarity(DateValue(1990), DateValue(1991)) == 0.3
    assert date_similarity(full, DateValue()) == 0.0


def test_date_parsing_and_rendering() -> None:
    assert DateValue.parse("1990-05-12") == DateValue(1990, 5, 12)
    assert DateValue.parse("12/05/1990") == DateValue(1990, 5, 12)
    assert DateValue.parse("1990") == DateValue(1990) and str(DateValue(1990)) == "1990"
    assert DateValue.parse("") == DateValue() and str(DateValue()) == "?"
    with pytest.raises(ValueError):
        DateValue.parse("12-05-1990x")


def test_phone_normalisation_and_similarity() -> None:
    assert (
        normalize_phone("+212 6 12 34 56 78")
        == normalize_phone("0612345678")
        == normalize_phone("00212612345678")
    )
    assert phone_similarity("0612345678", "+212612345678") == 1.0
    assert phone_similarity("0612345678", "0712345678") == 0.8  # same last 8 digits
    assert phone_similarity("0612345678", "0699999999") == 0.0
    assert phone_similarity("", "0612345678") == 0.0


def test_blocking_keys() -> None:
    record = PersonRecord(
        "p1", "El Amrani", "Mohamed", DateValue(1990), "Casa", "0612345678", "a@b.ma"
    )
    keys = blocking_keys(record)
    assert f"nom:{name_key('Lamrani')}" in keys
    assert "nom4:elam" in keys and "tel:12345678" in keys and "mail:a@b.ma" in keys
    assert blocking_keys(PersonRecord("p2", "Li", "A")) == {"nom:ll"}
    assert blocking_keys(PersonRecord("p3", "", "A")) == set()


def test_record_invariants() -> None:
    with pytest.raises(ValueError):
        PersonRecord("", "a", "b")
    with pytest.raises(ValueError):
        PersonRecord("p", "", " ")
    assert PersonRecord("p", "Tazi", "Sara").full_name == "Sara Tazi"
