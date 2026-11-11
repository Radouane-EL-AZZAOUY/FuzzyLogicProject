"""Runtime settings (environment variables; ``None`` means "use the packaged default")."""

from __future__ import annotations

import os
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path

ENV_PREFIX = "FUZZYSCOUT_"


@dataclass(frozen=True, slots=True)
class Settings:
    knowledge_dir: Path | None = None
    """Directory holding ``variables.toml``, ``positions.toml`` and the stage files."""
    players_csv: Path | None = None
    observations_csv: Path | None = None
    """Observations of the « commande Scout » system (see ``docs/10-commande-scout.md``)."""
    log_level: str = "INFO"

    @classmethod
    def from_env(cls, env: Mapping[str, str] | None = None) -> Settings:
        source = os.environ if env is None else env
        knowledge = source.get(f"{ENV_PREFIX}KNOWLEDGE_DIR", "").strip()
        players = source.get(f"{ENV_PREFIX}PLAYERS_CSV", "").strip()
        observations = source.get(f"{ENV_PREFIX}OBSERVATIONS_CSV", "").strip()
        return cls(
            knowledge_dir=Path(knowledge) if knowledge else None,
            players_csv=Path(players) if players else None,
            observations_csv=Path(observations) if observations else None,
            log_level=source.get(f"{ENV_PREFIX}LOG_LEVEL", "INFO").strip().upper() or "INFO",
        )

    def with_overrides(
        self,
        knowledge_dir: str | Path | None = None,
        players_csv: str | Path | None = None,
        observations_csv: str | Path | None = None,
    ) -> Settings:
        return Settings(
            knowledge_dir=Path(knowledge_dir) if knowledge_dir else self.knowledge_dir,
            players_csv=Path(players_csv) if players_csv else self.players_csv,
            observations_csv=(
                Path(observations_csv) if observations_csv else self.observations_csv
            ),
            log_level=self.log_level,
        )
