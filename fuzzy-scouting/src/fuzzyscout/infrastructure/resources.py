"""Locations of the resources shipped inside the package (knowledge bases, sample data)."""

from __future__ import annotations

from importlib import resources
from pathlib import Path


def package_root() -> Path:
    return Path(str(resources.files("fuzzyscout")))


def default_knowledge_dir() -> Path:
    return package_root() / "knowledge"


def default_players_csv() -> Path:
    return package_root() / "data" / "joueurs_exemple.csv"
