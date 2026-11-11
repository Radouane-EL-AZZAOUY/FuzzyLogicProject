"""Génère les observations SYNTHÉTIQUES du système de commande Scout.

Pour chaque joueur de ``joueurs_exemple.csv``, produit les neuf mesures dont se
déduisent la vitesse, l'accélération et le tacle. Pour illustrer les entrées floues,
une partie des cellules est volontairement imprécise : un intervalle (``4.0..4.3``)
ou une catégorie (``court``). Exécution reproductible (graine fixe) :

    python scripts/generate_command_observations.py [joueurs.csv] [sortie.csv]
"""

from __future__ import annotations

import csv
import random
import sys
from pathlib import Path

from fuzzyengine import LinguisticVariable, load_library

SEED = 2029
PACKAGE = Path(__file__).resolve().parents[1] / "src" / "fuzzyscout"
DEFAULT_PLAYERS = PACKAGE / "data" / "joueurs_exemple.csv"
DEFAULT_OUTPUT = PACKAGE / "data" / "observations_commande.csv"
LIBRARY = PACKAGE / "knowledge" / "variables.toml"

VARIABLES = [
    "vitesse_max_kmh",
    "temps_30m_s",
    "sprints_p90",
    "vitesse_changement_ms2",
    "distance_deplacement_m",
    "temps_reaction_s",
    "tacles_p90",
    "tacles_reussis_pct",
    "fautes_p90",
]
DECIMALS = {
    "vitesse_max_kmh": 1,
    "temps_30m_s": 2,
    "sprints_p90": 0,
    "vitesse_changement_ms2": 1,
    "distance_deplacement_m": 1,
    "temps_reaction_s": 2,
    "tacles_p90": 2,
    "tacles_reussis_pct": 0,
    "fautes_p90": 1,
}
# Demi-largeur des intervalles (incertitude typique de la mesure).
SPREAD = {
    "vitesse_max_kmh": 0.8,
    "temps_30m_s": 0.12,
    "sprints_p90": 3,
    "vitesse_changement_ms2": 0.5,
    "distance_deplacement_m": 0.7,
    "temps_reaction_s": 0.03,
    "tacles_p90": 0.4,
    "tacles_reussis_pct": 6,
    "fautes_p90": 0.3,
}
IMPRECISE_SHARE = 0.22
"""Part des cellules rendues imprécises (moitié intervalles, moitié catégories)."""

# Niveau de tacle attendu par poste : (tacles/90 faible, tacles/90 fort).
TACKLE_RANGE = {
    "gardien": (0.1, 0.6),
    "defenseur_central": (1.2, 3.6),
    "milieu_central": (1.2, 3.2),
    "ailier": (0.8, 2.0),
    "attaquant": (0.3, 1.0),
}


def _number(value: float, name: str) -> str:
    return f"{value:.{DECIMALS[name]}f}"


def _measures(rng: random.Random, row: dict[str, str]) -> dict[str, float]:
    position = row["poste"]
    speed = float(row["vitesse_max_kmh"] or rng.gauss(31.0, 0.8))
    z_speed = (speed - 33.0) / 1.6  # écart au joueur moyen, en « écarts-types »
    z_accel = 0.6 * z_speed + rng.gauss(0.0, 0.8)
    low, high = TACKLE_RANGE[position]
    tackles = float(row["tacles_p90"] or rng.uniform(low, high))
    z_tackle = (tackles - (low + high) / 2) / ((high - low) / 4) * 0.5 + rng.gauss(0.0, 0.7)
    reaction_bonus = 0.03 if position == "gardien" else 0.0
    return {
        "vitesse_max_kmh": speed,
        "temps_30m_s": 4.3 - 0.13 * z_speed + rng.gauss(0.0, 0.05),
        "sprints_p90": max(1.0, 18 + 5.0 * z_speed + rng.gauss(0.0, 2.5))
        if position != "gardien"
        else rng.uniform(2, 8),
        "vitesse_changement_ms2": 4.0 + 0.9 * z_accel + rng.gauss(0.0, 0.25),
        "distance_deplacement_m": 9.5 + 1.2 * z_accel + rng.gauss(0.0, 0.35),
        "temps_reaction_s": max(
            0.14, 0.28 - 0.035 * z_accel - reaction_bonus + rng.gauss(0.0, 0.015)
        ),
        "tacles_p90": tackles,
        "tacles_reussis_pct": min(95.0, max(25.0, 65 + 9.0 * z_tackle + rng.gauss(0.0, 3.0))),
        "fautes_p90": max(0.2, 1.6 - 0.45 * z_tackle + rng.gauss(0.0, 0.2)),
    }


def _cell(
    rng: random.Random, name: str, value: float, library: dict[str, LinguisticVariable]
) -> str:
    variable = library[name]
    value = variable.universe.clamp(value)
    draw = rng.random()
    if draw < IMPRECISE_SHARE / 2:
        lower = variable.universe.clamp(value - SPREAD[name])
        upper = variable.universe.clamp(value + SPREAD[name])
        return f"{_number(lower, name)}..{_number(upper, name)}"
    if draw < IMPRECISE_SHARE:
        degrees = variable.fuzzify(value)
        return max(degrees, key=lambda term: degrees[term])
    return _number(value, name)


def generate(players: Path, output: Path, seed: int = SEED) -> int:
    rng = random.Random(seed)
    library = load_library(LIBRARY)
    with players.open(encoding="utf-8-sig", newline="") as handle:
        rows = list(csv.DictReader(handle))
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=["id", "nom", "poste", *VARIABLES])
        writer.writeheader()
        for row in rows:
            measures = _measures(rng, row)
            cells = {name: _cell(rng, name, measures[name], library) for name in VARIABLES}
            writer.writerow({"id": row["id"], "nom": row["nom"], "poste": row["poste"], **cells})
    return len(rows)


if __name__ == "__main__":
    source = Path(sys.argv[1]) if len(sys.argv) > 1 else DEFAULT_PLAYERS
    target = Path(sys.argv[2]) if len(sys.argv) > 2 else DEFAULT_OUTPUT
    written = generate(source, target)
    print(f"Observations de {written} joueurs écrites dans {target}")
