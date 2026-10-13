"""Shared fixtures: a small, fully-known fuzzy system used across engine tests."""

from __future__ import annotations

import pytest

from fuzzyengine import (
    FuzzySet,
    FuzzySystem,
    FuzzySystemBuilder,
    LinguisticVariable,
    RampDown,
    RampUp,
    Trapezoidal,
    Triangular,
    Universe,
    parse_rule,
)


@pytest.fixture
def vitesse() -> LinguisticVariable:
    return LinguisticVariable(
        "vitesse",
        Universe(0, 100),
        (
            FuzzySet("lente", RampDown(20, 40)),
            FuzzySet("moyenne", Triangular(30, 50, 70)),
            FuzzySet("rapide", RampUp(60, 80)),
        ),
        unit="km/h",
    )


@pytest.fixture
def age() -> LinguisticVariable:
    return LinguisticVariable(
        "age",
        Universe(16, 40),
        (
            FuzzySet("jeune", RampDown(22, 26)),
            FuzzySet("mature", Triangular(24, 29, 33)),
            FuzzySet("veteran", RampUp(31, 34)),
        ),
        unit="ans",
    )


@pytest.fixture
def score() -> LinguisticVariable:
    return LinguisticVariable(
        "score",
        Universe(0, 100),
        (
            FuzzySet("faible", Trapezoidal(0, 0, 25, 45)),
            FuzzySet("moyen", Triangular(30, 50, 70)),
            FuzzySet("bon", Triangular(55, 70, 85)),
            FuzzySet("excellent", Trapezoidal(72, 88, 100, 100)),
        ),
    )


@pytest.fixture
def demo_system(
    vitesse: LinguisticVariable, age: LinguisticVariable, score: LinguisticVariable
) -> FuzzySystem:
    rules = [
        parse_rule("SI vitesse EST rapide ET age EST jeune ALORS score EST excellent", "R1"),
        parse_rule("SI vitesse EST rapide ET age N'EST PAS jeune ALORS score EST bon", "R2"),
        parse_rule("SI vitesse EST moyenne ALORS score EST moyen", "R3"),
        parse_rule("SI vitesse EST lente ALORS score EST faible", "R4", weight=0.8),
    ]
    return (
        FuzzySystemBuilder("demo", "système de démonstration")
        .add_input(vitesse)
        .add_input(age)
        .add_output(score)
        .add_rules(rules)
        .build()
    )
