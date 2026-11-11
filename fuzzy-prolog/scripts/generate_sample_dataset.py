"""Régénère le jeu de données synthétique embarqué dans le paquet identitylink.

python scripts/generate_sample_dataset.py [répertoire] [--persons N] [--seed S]
"""

from __future__ import annotations

import argparse
from pathlib import Path

from identitylink.infrastructure.synthetic import generate_dataset

DEFAULT = Path(__file__).resolve().parents[1] / "src" / "identitylink" / "data"

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("out", nargs="?", default=str(DEFAULT))
    parser.add_argument("--persons", type=int, default=150)
    parser.add_argument("--seed", type=int, default=7)
    args = parser.parse_args()
    records, truth, count = generate_dataset(Path(args.out), args.persons, args.seed)
    print(f"{count} fiches -> {records}\nvérité -> {truth}")
