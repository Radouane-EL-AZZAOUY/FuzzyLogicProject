"""The fuzzy inference system: fuzzify → infer → defuzzify, with a full trace.

In the vocabulary of the course a :class:`FuzzySystem` is a *système formel*:

* alphabet      : the linguistic variables and their terms;
* language      : the well-formed formulas built with ``IS``, ``NOT``, ``AND``, ``OR``;
* axioms        : the rule base (plus, at run time, the fuzzified facts);
* inference     : generalised modus ponens (:mod:`fuzzyengine.inference`).

A *derivation* of the system is one call to :meth:`FuzzySystem.evaluate`.
"""

from __future__ import annotations

from collections.abc import Iterable, Mapping
from dataclasses import dataclass, field

from fuzzyengine.defuzzification import Centroid, Defuzzifier
from fuzzyengine.exceptions import DefinitionError
from fuzzyengine.fuzzification import Fuzzifier
from fuzzyengine.inference import InferenceMethod, MamdaniInference, RuleActivation
from fuzzyengine.observations import Observation
from fuzzyengine.rules import Rule, RuleBase
from fuzzyengine.variables import LinguisticVariable


@dataclass(frozen=True, slots=True)
class EvaluationResult:
    """Everything produced by one evaluation (crisp outputs + explanation trace)."""

    system_name: str
    inputs: dict[str, float]
    """Precise inputs actually used (after clamping); imprecise inputs are absent."""
    fuzzified_inputs: dict[str, dict[str, float]]
    activations: tuple[RuleActivation, ...]
    outputs: dict[str, float]
    """Crisp outputs."""
    fuzzified_outputs: dict[str, dict[str, float]]
    """Degree of the crisp output in every output term (linguistic reading of the result)."""
    warnings: tuple[str, ...] = ()
    observations: dict[str, Observation] = field(default_factory=dict)
    """Every input as it was used: precise value, interval, category or degrees."""
    conclusions: dict[str, dict[str, float]] = field(default_factory=dict)
    """Degree to which the rules concluded each output term (before defuzzification)."""

    def fired_rules(self, minimum_strength: float = 0.0) -> list[RuleActivation]:
        """Activations with strength above ``minimum_strength``, strongest first."""
        fired = [a for a in self.activations if a.strength > minimum_strength]
        return sorted(fired, key=lambda a: a.strength, reverse=True)

    def label(self, output: str) -> str:
        """Linguistic term best describing the crisp value of ``output``."""
        degrees = self.fuzzified_outputs[output]
        return max(degrees, key=lambda term: degrees[term])


@dataclass(frozen=True, slots=True)
class FuzzySystem:
    name: str
    inputs: dict[str, LinguisticVariable]
    outputs: dict[str, LinguisticVariable]
    rule_base: RuleBase
    inference: InferenceMethod = field(default_factory=MamdaniInference)
    defuzzifier: Defuzzifier = field(default_factory=Centroid)
    description: str = ""
    _fuzzifier: Fuzzifier = field(init=False, repr=False, compare=False)

    def __post_init__(self) -> None:
        if not self.name.strip():
            raise DefinitionError("Un système flou doit avoir un nom.")
        if not self.inputs or not self.outputs:
            raise DefinitionError(
                f"Le système '{self.name}' doit déclarer au moins une entrée et une sortie."
            )
        clash = set(self.inputs) & set(self.outputs)
        if clash:
            raise DefinitionError(
                f"Système '{self.name}' : variable(s) à la fois en entrée et en sortie : "
                f"{', '.join(sorted(clash))}."
            )
        for key, variable in {**self.inputs, **self.outputs}.items():
            if key != variable.name:
                raise DefinitionError(
                    f"Système '{self.name}' : la clé '{key}' ne correspond pas au nom "
                    f"de variable '{variable.name}'."
                )
        self.rule_base.validate(self.inputs, self.outputs)
        object.__setattr__(self, "_fuzzifier", Fuzzifier(self.inputs))

    @property
    def input_names(self) -> tuple[str, ...]:
        return tuple(self.inputs)

    @property
    def output_names(self) -> tuple[str, ...]:
        return tuple(self.outputs)

    def evaluate(self, values: Mapping[str, Observation]) -> EvaluationResult:
        """Run one full derivation for the observed ``values`` (extra keys are ignored).

        Each value is a precise number, an interval, a category or explicit degrees.
        """
        fuzzified = self._fuzzifier.fuzzify(values)
        outcome = self.inference.infer(self.rule_base, fuzzified.interpretation, self.outputs)
        warnings = list(fuzzified.warnings)
        crisp: dict[str, float] = {}
        fuzzified_outputs: dict[str, dict[str, float]] = {}
        conclusions: dict[str, dict[str, float]] = {}
        for name, variable in self.outputs.items():
            distribution = outcome.distributions[name]
            conclusions[name] = distribution.term_strengths()
            value = self.defuzzifier.defuzzify(distribution.membership, variable.universe)
            if value is None:
                warnings.append(
                    f"Aucune règle n'a conclu sur '{name}' (ensemble de sortie vide) : "
                    f"valeur par défaut (milieu de l'univers) utilisée."
                )
                value = variable.universe.midpoint
            crisp[name] = value
            fuzzified_outputs[name] = variable.fuzzify(value)
        return EvaluationResult(
            system_name=self.name,
            inputs=fuzzified.values,
            fuzzified_inputs=fuzzified.interpretation.as_dict(),
            activations=outcome.activations,
            outputs=crisp,
            fuzzified_outputs=fuzzified_outputs,
            warnings=tuple(warnings),
            observations=fuzzified.observations,
            conclusions=conclusions,
        )


class FuzzySystemBuilder:
    """Fluent helper to assemble a :class:`FuzzySystem` from code.

    >>> system = (FuzzySystemBuilder("demo")
    ...     .add_input(speed).add_output(risk).add_rules(rules).build())
    """

    def __init__(self, name: str, description: str = "") -> None:
        self._name = name
        self._description = description
        self._inputs: dict[str, LinguisticVariable] = {}
        self._outputs: dict[str, LinguisticVariable] = {}
        self._rules: list[Rule] = []
        self._inference: InferenceMethod | None = None
        self._defuzzifier: Defuzzifier | None = None

    def add_input(self, variable: LinguisticVariable) -> FuzzySystemBuilder:
        self._inputs[variable.name] = variable
        return self

    def add_output(self, variable: LinguisticVariable) -> FuzzySystemBuilder:
        self._outputs[variable.name] = variable
        return self

    def add_rule(self, rule: Rule) -> FuzzySystemBuilder:
        self._rules.append(rule)
        return self

    def add_rules(self, rules: Iterable[Rule]) -> FuzzySystemBuilder:
        self._rules.extend(rules)
        return self

    def with_inference(self, inference: InferenceMethod) -> FuzzySystemBuilder:
        self._inference = inference
        return self

    def with_defuzzifier(self, defuzzifier: Defuzzifier) -> FuzzySystemBuilder:
        self._defuzzifier = defuzzifier
        return self

    def build(self) -> FuzzySystem:
        return FuzzySystem(
            name=self._name,
            description=self._description,
            inputs=dict(self._inputs),
            outputs=dict(self._outputs),
            rule_base=RuleBase(tuple(self._rules)),
            inference=self._inference or MamdaniInference(),
            defuzzifier=self._defuzzifier or Centroid(),
        )
