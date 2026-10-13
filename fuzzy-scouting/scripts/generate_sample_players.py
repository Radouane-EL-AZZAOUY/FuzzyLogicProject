"""Génère le jeu de données SYNTHÉTIQUE de démonstration ``joueurs_exemple.csv``.

Toutes les identités (noms, clubs) sont fictives ; les statistiques sont tirées de
distributions plausibles conditionnées par le poste et par un facteur de qualité
caché ``q`` (0 = faible, 1 = excellent), ce qui permet de vérifier que le système
retrouve bien les meilleurs profils. Exécution reproductible (graine fixe) :

    python scripts/generate_sample_players.py [chemin_de_sortie.csv]
"""

from __future__ import annotations

import csv
import random
import sys
from pathlib import Path

SEED = 2024
DEFAULT_OUTPUT = (
    Path(__file__).resolve().parents[1] / "src" / "fuzzyscout" / "data" / "joueurs_exemple.csv"
)

FIRST_NAMES = [
    "Yassine",
    "Amine",
    "Omar",
    "Ilias",
    "Rayan",
    "Mehdi",
    "Anas",
    "Hamza",
    "Zakaria",
    "Ayoub",
    "Walid",
    "Nabil",
    "Karim",
    "Sofiane",
    "Bilal",
    "Idris",
    "Noah",
    "Lucas",
    "Mateo",
    "Diego",
    "Tiago",
    "Moussa",
    "Ismaël",
    "Elias",
    "Jonas",
    "Adam",
    "Samir",
    "Reda",
    "Tarik",
    "Younes",
    "Kenzo",
    "Malik",
    "Nassim",
    "Ilyes",
    "Ayman",
    "Oussama",
    "Rachid",
    "Driss",
    "Soufiane",
    "Hicham",
]
LAST_NAMES = [
    "Bennani",
    "El Amrani",
    "Tazi",
    "Chraibi",
    "Lahlou",
    "Berrada",
    "Fassi",
    "Kabbaj",
    "Sefrioui",
    "Alaoui",
    "Benjelloun",
    "Ouazzani",
    "Haddad",
    "Mansouri",
    "Zerouali",
    "Daoudi",
    "Rami",
    "Saidi",
    "Ferreira",
    "Moreno",
    "Dubois",
    "Lambert",
    "Diallo",
    "Ndiaye",
    "Kone",
    "Traoré",
    "Rossi",
    "Costa",
    "Hernández",
    "Martins",
    "Bakkali",
    "Lamrani",
    "Ziani",
    "Belkadi",
    "Cherkaoui",
    "Hajji",
    "Kettani",
    "Nejjar",
    "Raji",
    "Slaoui",
]
CLUBS = [
    "FC Atlas",
    "Olympique du Détroit",
    "Racing Sahara",
    "AS Rif",
    "Union Chaouia",
    "Sporting Souss",
    "Étoile de l'Oriental",
    "Dynamo Zerhoun",
    "Stade Tensift",
    "Athletic Bouregreg",
]
NATIONALITIES = ["MA", "MA", "MA", "FR", "ES", "SN", "CI", "DZ", "TN", "PT", "EG", "NG"]

# Paramètres (lo, hi, écart-type) : moyenne = lo + q * (hi - lo). ``hi`` < ``lo``
# signifie « plus petit = meilleur » (ex. buts encaissés).
OUTFIELD_BASE: dict[str, tuple[float, float, float]] = {
    "buts_p90": (0.0, 0.15, 0.03),
    "xg_p90": (0.02, 0.15, 0.03),
    "passes_decisives_p90": (0.02, 0.15, 0.03),
    "tirs_cadres_pct": (25, 45, 5),
    "passes_cles_p90": (0.3, 1.2, 0.2),
    "precision_passes_pct": (72, 88, 2.5),
    "passes_progressives_p90": (2.0, 5.0, 0.6),
    "dribbles_p90": (0.5, 2.0, 0.3),
    "dribbles_reussis_pct": (40, 58, 5),
    "tacles_p90": (0.8, 2.0, 0.3),
    "interceptions_p90": (0.6, 1.5, 0.25),
    "duels_aeriens_pct": (40, 58, 5),
    "vitesse_max_kmh": (30.5, 35.0, 0.7),
    "distance_km_p90": (9.6, 11.8, 0.35),
}

PROFILES: dict[str, dict[str, tuple[float, float, float]]] = {
    "attaquant": {
        "buts_p90": (0.15, 0.85, 0.08),
        "xg_p90": (0.2, 0.75, 0.07),
        "tirs_cadres_pct": (30, 58, 4),
        "passes_cles_p90": (0.6, 2.2, 0.3),
        "passes_decisives_p90": (0.05, 0.3, 0.05),
        "dribbles_p90": (1.0, 3.2, 0.4),
        "duels_aeriens_pct": (40, 62, 5),
        "tacles_p90": (0.3, 1.0, 0.2),
        "interceptions_p90": (0.3, 0.9, 0.15),
        "passes_progressives_p90": (1.5, 3.5, 0.5),
        "precision_passes_pct": (68, 82, 2.5),
    },
    "ailier": {
        "dribbles_p90": (1.8, 5.8, 0.5),
        "dribbles_reussis_pct": (42, 68, 4),
        "passes_decisives_p90": (0.08, 0.45, 0.06),
        "buts_p90": (0.08, 0.5, 0.07),
        "xg_p90": (0.1, 0.4, 0.06),
        "passes_cles_p90": (0.8, 2.8, 0.3),
        "tirs_cadres_pct": (30, 50, 5),
        "vitesse_max_kmh": (32.0, 36.0, 0.6),
        "distance_km_p90": (10.0, 11.8, 0.35),
    },
    "milieu_central": {
        "precision_passes_pct": (76, 92, 2),
        "passes_progressives_p90": (3.0, 9.0, 0.7),
        "passes_cles_p90": (0.6, 2.6, 0.3),
        "interceptions_p90": (0.9, 2.6, 0.3),
        "tacles_p90": (1.2, 3.2, 0.4),
        "buts_p90": (0.02, 0.2, 0.04),
        "xg_p90": (0.03, 0.2, 0.04),
        "distance_km_p90": (10.5, 12.5, 0.35),
        "vitesse_max_kmh": (30.0, 34.5, 0.7),
        "dribbles_p90": (0.8, 2.5, 0.3),
    },
    "defenseur_central": {
        "tacles_p90": (1.2, 3.6, 0.4),
        "interceptions_p90": (1.0, 3.0, 0.3),
        "duels_aeriens_pct": (50, 74, 4),
        "precision_passes_pct": (76, 92, 2.5),
        "passes_progressives_p90": (2.5, 6.5, 0.6),
        "buts_p90": (0.0, 0.12, 0.03),
        "xg_p90": (0.02, 0.12, 0.03),
        "vitesse_max_kmh": (30.0, 34.0, 0.7),
        "distance_km_p90": (9.6, 11.0, 0.3),
        "dribbles_p90": (0.2, 1.0, 0.2),
        "dribbles_reussis_pct": (40, 60, 5),
    },
    "gardien": {
        "arrets_pct": (62, 80, 2),
        "buts_encaisses_p90": (1.8, 0.7, 0.15),
        "sorties_aeriennes_p90": (0.5, 2.0, 0.25),
        "precision_passes_pct": (60, 88, 4),
    },
}

HEIGHT_RANGE: dict[str, tuple[int, int]] = {
    "attaquant": (176, 192),
    "ailier": (168, 184),
    "milieu_central": (172, 188),
    "defenseur_central": (182, 196),
    "gardien": (183, 197),
}

COUNTS: dict[str, int] = {
    "gardien": 6,
    "defenseur_central": 8,
    "milieu_central": 9,
    "ailier": 8,
    "attaquant": 9,
}

COLUMNS = [
    "id",
    "nom",
    "club",
    "nationalite",
    "poste",
    "age",
    "taille_cm",
    "minutes_jouees",
    "blessures_jours",
    "contrat_mois_restants",
    "valeur_marche_meur",
    "buts_p90",
    "xg_p90",
    "passes_decisives_p90",
    "tirs_cadres_pct",
    "passes_cles_p90",
    "precision_passes_pct",
    "passes_progressives_p90",
    "dribbles_p90",
    "dribbles_reussis_pct",
    "tacles_p90",
    "interceptions_p90",
    "duels_aeriens_pct",
    "vitesse_max_kmh",
    "distance_km_p90",
    "arrets_pct",
    "buts_encaisses_p90",
    "sorties_aeriennes_p90",
]


def _draw(rng: random.Random, spec: tuple[float, float, float], q: float) -> float:
    lo, hi, sd = spec
    return rng.gauss(lo + q * (hi - lo), sd)


def _market_value(rng: random.Random, q: float, age: int) -> float:
    age_factor = 1.25 if age <= 23 else 1.0 if age <= 29 else 0.6 if age <= 32 else 0.35
    return round(max(0.2, (0.5 + 40 * q * q) * age_factor * rng.uniform(0.8, 1.2)), 1)


def _player_row(rng: random.Random, identifier: str, position: str, name: str) -> dict[str, object]:
    q = rng.uniform(0.1, 0.95)
    age = rng.randint(18, 34)
    specs = dict(OUTFIELD_BASE) if position != "gardien" else {}
    specs.update(PROFILES[position])
    if position != "gardien":
        specs.pop("arrets_pct", None)
    row: dict[str, object] = {
        "id": identifier,
        "nom": name,
        "club": rng.choice(CLUBS),
        "nationalite": rng.choice(NATIONALITIES),
        "poste": position,
        "age": age,
        "taille_cm": rng.randint(*HEIGHT_RANGE[position]),
        "minutes_jouees": int(min(3600, max(300, rng.gauss(1400 + 1600 * q, 500)))),
        "blessures_jours": int(max(0, rng.gauss(30 + 25 * (1 - q), 30))),
        "contrat_mois_restants": rng.randint(3, 48),
        "valeur_marche_meur": _market_value(rng, q, age),
    }
    for column in COLUMNS[11:]:
        spec = specs.get(column)
        if spec is None:
            row[column] = ""
            continue
        value = _draw(rng, spec, q)
        if column.endswith("_pct"):
            value = min(max(value, 5.0), 95.0)
        row[column] = round(max(0.0, value), 2 if value < 10 else 1)
    return row


def generate(output: Path, seed: int = SEED) -> int:
    rng = random.Random(seed)
    names = [f"{f} {n}" for f in FIRST_NAMES for n in LAST_NAMES]
    rng.shuffle(names)
    rows: list[dict[str, object]] = []
    index = 0
    for position, count in COUNTS.items():
        for _ in range(count):
            index += 1
            rows.append(_player_row(rng, f"P{index:03d}", position, names.pop()))
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=COLUMNS)
        writer.writeheader()
        writer.writerows(rows)
    return len(rows)


if __name__ == "__main__":
    target = Path(sys.argv[1]) if len(sys.argv) > 1 else DEFAULT_OUTPUT
    written = generate(target)
    print(f"{written} joueurs synthétiques écrits dans {target}")
