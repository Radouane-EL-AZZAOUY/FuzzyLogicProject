"""Builds (and caches) the inference pipeline of a position from TOML knowledge bases."""

from __future__ import annotations

from pathlib import Path

from fuzzyengine import (
    FuzzyPipeline,
    KnowledgeBaseError,
    LinguisticVariable,
    load_library,
    load_pipeline,
)
from fuzzyscout.domain.position import Position

LIBRARY_FILE = "variables.toml"
COMMAND_DIR = "commande"
COMMAND_STAGES = ("vitesse.toml", "acceleration.toml", "tacle.toml", "niveau.toml")
"""Stages of the « commande Scout » system: three deductions, then the decision."""


class TomlPipelineProvider:
    """Knowledge directory layout::

    knowledge/
      variables.toml          # shared linguistic variables (library)
      positions.toml          # position catalogue
      technique/<poste>.toml  # one stage per file, referenced by positions.toml
      physique/..., profil/..., aptitude/...
      commande/               # the « commande Scout » system (optional)
    """

    def __init__(self, knowledge_dir: str | Path, library_file: str = LIBRARY_FILE) -> None:
        self._dir = Path(knowledge_dir)
        self._library_path = self._dir / library_file
        self._library: dict[str, LinguisticVariable] | None = None
        self._cache: dict[str, FuzzyPipeline] = {}
        self._command: FuzzyPipeline | None = None

    @property
    def knowledge_dir(self) -> Path:
        return self._dir

    def library(self) -> dict[str, LinguisticVariable]:
        if self._library is None:
            self._library = load_library(self._library_path) if self._library_path.exists() else {}
        return self._library

    def pipeline_for(self, position: Position) -> FuzzyPipeline:
        pipeline = self._cache.get(position.code)
        if pipeline is None:
            pipeline = load_pipeline(
                name=position.code,
                paths=[self._dir / stage for stage in position.stages],
                description=position.label,
                library=self.library(),
            )
            if len(pipeline.final_outputs) != 1:
                raise KnowledgeBaseError(
                    f"[poste {position.code}] la dernière étape doit produire exactement une "
                    f"sortie (l'aptitude), trouvé : "
                    f"{', '.join(pipeline.final_outputs) or 'aucune'}."
                )
            self._cache[position.code] = pipeline
        return pipeline

    @property
    def has_command(self) -> bool:
        return (self._dir / COMMAND_DIR).is_dir()

    def command_pipeline(self) -> FuzzyPipeline:
        """The « commande Scout » system: each linguistic variable is deduced by its own
        stage and handed to the final stage as a fuzzy conclusion (no defuzzification
        in between)."""
        if self._command is None:
            pipeline = load_pipeline(
                name="commande_scout",
                paths=[self._dir / COMMAND_DIR / stage for stage in COMMAND_STAGES],
                description="Système de commande Scout",
                library=self.library(),
                chaining="fuzzy",
            )
            if len(pipeline.final_outputs) != 1:
                raise KnowledgeBaseError(
                    "[commande_scout] la dernière étape doit produire exactement une sortie "
                    f"(le niveau), trouvé : {', '.join(pipeline.final_outputs) or 'aucune'}."
                )
            self._command = pipeline
        return self._command

    def clear(self) -> None:
        """Forget cached pipelines (e.g. after editing knowledge bases on disk)."""
        self._cache.clear()
        self._command = None
        self._library = None
