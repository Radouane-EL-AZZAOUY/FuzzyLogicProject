"""Packaged knowledge (rules, similarities) and sample data locations."""

from __future__ import annotations

from importlib import resources
from pathlib import Path


def _package_root() -> Path:
    return Path(str(resources.files("identitylink")))


def default_records_csv() -> Path:
    return _package_root() / "data" / "personnes_exemple.csv"


def default_truth_csv() -> Path:
    return _package_root() / "data" / "verite_exemple.csv"


class PackagedKnowledge:
    """Rules and similarities shipped with the package, or overridden by files."""

    def __init__(
        self, rules_path: str | Path | None = None, similarities_path: str | Path | None = None
    ) -> None:
        knowledge = _package_root() / "knowledge"
        self._rules = Path(rules_path) if rules_path else knowledge / "regles.pl"
        self._similarities = (
            Path(similarities_path) if similarities_path else knowledge / "similarites.pl"
        )

    @property
    def rules_path(self) -> Path:
        return self._rules

    @property
    def similarities_path(self) -> Path:
        return self._similarities

    def rules(self) -> str:
        return self._rules.read_text(encoding="utf-8")

    def similarities(self) -> str:
        return self._similarities.read_text(encoding="utf-8")
