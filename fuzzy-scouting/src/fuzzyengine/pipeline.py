"""Hierarchical (chained) fuzzy systems.

Chaining systems keeps rule bases small: with *n* inputs of *k* terms a flat
system needs up to *kⁿ* rules, whereas a hierarchy of small systems grows
linearly. The outputs of a stage become inputs of the next ones, exactly like a
proof ``E1, E2, …, En`` where each step may use the theorems established before
(course, *Systèmes formels*).

Two ways of handing a conclusion to the next stage (``chaining``):

* ``"crisp"`` — the conclusion is defuzzified and the number is fuzzified again by
  the next stage (simple, but the shape of the conclusion is lost);
* ``"fuzzy"`` — the next stage receives the conclusion itself, i.e. the degree of
  each term (``vitesse : fort 0.7, moyenne 0.3``). Nothing is lost in between; the
  defuzzified number is still computed, for display only.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass

from fuzzyengine.exceptions import DefinitionError
from fuzzyengine.observations import Degrees, Observation
from fuzzyengine.system import EvaluationResult, FuzzySystem

CHAININGS = ("crisp", "fuzzy")


@dataclass(frozen=True, slots=True)
class PipelineResult:
    pipeline_name: str
    stages: tuple[EvaluationResult, ...]
    outputs: dict[str, float]
    """Every crisp value produced by any stage."""
    labels: dict[str, str]
    """Linguistic label of every produced output."""

    @property
    def warnings(self) -> tuple[str, ...]:
        return tuple(w for stage in self.stages for w in stage.warnings)

    def stage(self, system_name: str) -> EvaluationResult:
        for result in self.stages:
            if result.system_name == system_name:
                return result
        raise KeyError(system_name)


@dataclass(frozen=True, slots=True)
class FuzzyPipeline:
    name: str
    stages: tuple[FuzzySystem, ...]
    description: str = ""
    chaining: str = "crisp"

    def __post_init__(self) -> None:
        if self.chaining not in CHAININGS:
            raise DefinitionError(
                f"Pipeline '{self.name}' : chaînage inconnu '{self.chaining}' "
                f"(attendu : {' ou '.join(CHAININGS)})."
            )
        if not self.stages:
            raise DefinitionError(f"Le pipeline '{self.name}' doit avoir au moins une étape.")
        produced: set[str] = set()
        names: set[str] = set()
        for index, stage in enumerate(self.stages):
            if stage.name in names:
                raise DefinitionError(
                    f"Pipeline '{self.name}' : étape '{stage.name}' présente deux fois."
                )
            names.add(stage.name)
            duplicated = produced & set(stage.outputs)
            if duplicated:
                raise DefinitionError(
                    f"Pipeline '{self.name}' : sortie(s) produite(s) par plusieurs étapes : "
                    f"{', '.join(sorted(duplicated))}."
                )
            later = {
                name for later_stage in self.stages[index + 1 :] for name in later_stage.outputs
            }
            forward = set(stage.inputs) & later
            if forward:
                raise DefinitionError(
                    f"Pipeline '{self.name}' : l'étape '{stage.name}' consomme "
                    f"{', '.join(sorted(forward))}, produit(s) par une étape ultérieure ; "
                    "réordonner les étapes."
                )
            produced |= set(stage.outputs)

    @property
    def required_inputs(self) -> tuple[str, ...]:
        """External inputs: consumed by a stage and produced by no earlier stage."""
        produced: set[str] = set()
        required: list[str] = []
        for stage in self.stages:
            for name in stage.inputs:
                if name not in produced and name not in required:
                    required.append(name)
            produced |= set(stage.outputs)
        return tuple(required)

    @property
    def produced_outputs(self) -> tuple[str, ...]:
        return tuple(name for stage in self.stages for name in stage.outputs)

    @property
    def final_outputs(self) -> tuple[str, ...]:
        return tuple(self.stages[-1].outputs)

    def evaluate(self, values: Mapping[str, Observation]) -> PipelineResult:
        context: dict[str, Observation] = dict(values)
        results: list[EvaluationResult] = []
        outputs: dict[str, float] = {}
        labels: dict[str, str] = {}
        for stage in self.stages:
            result = stage.evaluate(context)
            results.append(result)
            for name, value in result.outputs.items():
                context[name] = self._handed_over(result, name)
                outputs[name] = value
                labels[name] = result.label(name)
        return PipelineResult(self.name, tuple(results), outputs, labels)

    def _handed_over(self, result: EvaluationResult, name: str) -> Observation:
        """What the following stages receive for the output ``name`` of ``result``."""
        conclusion = result.conclusions[name]
        if self.chaining == "fuzzy" and any(degree > 0.0 for degree in conclusion.values()):
            return Degrees(conclusion)
        # Crisp chaining, or no rule fired (the stage fell back to a default number).
        return result.outputs[name]
