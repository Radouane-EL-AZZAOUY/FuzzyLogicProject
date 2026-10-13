"""The packaged knowledge bases must load, validate and cover their input space."""

from __future__ import annotations

import random
from itertools import pairwise

import pytest

from fuzzyscout.domain.errors import PositionNotFoundError
from fuzzyscout.infrastructure.toml_pipeline_provider import TomlPipelineProvider
from fuzzyscout.infrastructure.toml_position_catalog import TomlPositionCatalog

EXPECTED_POSITIONS = {"gardien", "defenseur_central", "milieu_central", "ailier", "attaquant"}


def test_catalog_lists_expected_positions(positions: TomlPositionCatalog) -> None:
    assert {p.code for p in positions.all()} == EXPECTED_POSITIONS
    assert positions.get("attaquant").label.startswith("Attaquant")
    with pytest.raises(PositionNotFoundError, match="Postes connus"):
        positions.get("libero")


def test_every_position_pipeline_loads_and_ends_with_aptitude(
    positions: TomlPositionCatalog, pipelines: TomlPipelineProvider
) -> None:
    for position in positions.all():
        pipeline = pipelines.pipeline_for(position)
        assert pipeline.final_outputs == ("aptitude",)
        assert set(pipeline.produced_outputs) == {"technique", "physique", "profil", "aptitude"}
        assert all(len(stage.rule_base) >= 8 for stage in pipeline.stages)
        assert pipelines.pipeline_for(position) is pipeline  # cached


def test_rule_bases_cover_the_whole_input_space(
    positions: TomlPositionCatalog, pipelines: TomlPipelineProvider
) -> None:
    """For random inputs inside the universes, every stage must fire at least one rule."""
    rng = random.Random(7)
    for position in positions.all():
        pipeline = pipelines.pipeline_for(position)
        variables = {name: var for stage in pipeline.stages for name, var in stage.inputs.items()}
        for _ in range(300):
            values = {
                name: rng.uniform(var.universe.lower, var.universe.upper)
                for name, var in variables.items()
                if name in pipeline.required_inputs
            }
            result = pipeline.evaluate(values)
            uncovered = [w for w in result.warnings if "Aucune règle" in w]
            assert not uncovered, f"{position.code} {values}: {uncovered}"


def test_scores_are_monotonic_in_the_key_statistic(
    pipelines: TomlPipelineProvider, positions: TomlPositionCatalog
) -> None:
    pipeline = pipelines.pipeline_for(positions.get("attaquant"))
    base = {
        "xg_p90": 0.5,
        "tirs_cadres_pct": 48,
        "passes_cles_p90": 1.5,
        "vitesse_max_kmh": 34,
        "distance_km_p90": 10.8,
        "duels_aeriens_pct": 55,
        "taille_cm": 184,
        "age": 25,
        "minutes_jouees": 2500,
        "blessures_jours": 10,
    }
    scores = [
        pipeline.evaluate({**base, "buts_p90": goals}).outputs["aptitude"]
        for goals in (0.1, 0.3, 0.5, 0.7, 0.9)
    ]
    # Mamdani + centroïde : monotone à une tolérance numérique près (plateaux des termes)
    assert all(later >= earlier - 1.0 for earlier, later in pairwise(scores))
    assert scores[-1] - scores[0] > 20
