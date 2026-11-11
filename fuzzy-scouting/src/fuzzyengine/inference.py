"""Inference: generalised modus ponens over a rule base (Mamdani method).

Classical modus ponens (course, *Règles d'inférence*)::

    G → H,  G  ⊢  H

Generalised modus ponens: from ``G → H`` and a premise ``G'`` true to degree α we
conclude ``H'``, a fuzzy set obtained by *implication* of ``H`` at strength α. All
rules fire in parallel (forward chaining) and their conclusions about the same
output are *aggregated* with a t-conorm.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import Mapping
from dataclasses import dataclass

from fuzzyengine.formulas import Atom, Interpretation
from fuzzyengine.operators import (
    ZADEH,
    BinaryOperator,
    FuzzyOperators,
    Implication,
    MaximumSNorm,
    MinimumImplication,
)
from fuzzyengine.rules import Consequent, Rule, RuleBase
from fuzzyengine.variables import LinguisticVariable


@dataclass(frozen=True, slots=True)
class AtomEvaluation:
    atom: Atom
    degree: float


@dataclass(frozen=True, slots=True)
class RuleActivation:
    """Trace of one rule for explainability."""

    rule: Rule
    antecedent_truth: float
    strength: float
    """Firing strength α = weight × truth(antecedent)."""
    atom_degrees: tuple[AtomEvaluation, ...]

    @property
    def fired(self) -> bool:
        return self.strength > 0.0


@dataclass(frozen=True, slots=True)
class Contribution:
    """One implied conclusion ``variable IS term`` at a given strength."""

    rule_identifier: str
    consequent: Consequent
    strength: float


@dataclass(frozen=True, slots=True)
class OutputDistribution:
    """Aggregated fuzzy conclusion for one output variable (a fuzzy *theorem*)."""

    variable: LinguisticVariable
    contributions: tuple[Contribution, ...]
    implication: Implication
    aggregation: BinaryOperator

    def membership(self, x: float) -> float:
        """μ of the aggregated output set at ``x``."""
        result = 0.0
        for contribution in self.contributions:
            if contribution.strength <= 0.0:
                continue
            term_degree = self.variable.term(contribution.consequent.term).degree(x)
            implied = self.implication(contribution.strength, term_degree)
            result = self.aggregation(result, implied)
        return result

    @property
    def is_empty(self) -> bool:
        return all(c.strength <= 0.0 for c in self.contributions)

    def term_strengths(self) -> dict[str, float]:
        """Degree to which the rules concluded each term (aggregated firing strengths).

        This is the fuzzy conclusion *before* defuzzification, in linguistic form:
        ``{faible: 0.0, moyenne: 0.3, fort: 0.7}``.
        """
        strengths = dict.fromkeys(self.variable.labels, 0.0)
        for contribution in self.contributions:
            term = contribution.consequent.term
            strengths[term] = self.aggregation(strengths[term], contribution.strength)
        return strengths


@dataclass(frozen=True, slots=True)
class InferenceOutcome:
    activations: tuple[RuleActivation, ...]
    distributions: dict[str, OutputDistribution]


class InferenceMethod(ABC):
    """Strategy turning a rule base + interpretation into fuzzy conclusions."""

    @abstractmethod
    def infer(
        self,
        rule_base: RuleBase,
        interpretation: Interpretation,
        outputs: Mapping[str, LinguisticVariable],
    ) -> InferenceOutcome: ...


class MamdaniInference(InferenceMethod):
    """Max-min (or configurable) Mamdani inference."""

    def __init__(
        self,
        operators: FuzzyOperators = ZADEH,
        implication: Implication | None = None,
        aggregation: BinaryOperator | None = None,
    ) -> None:
        self.operators = operators
        self.implication: Implication = implication or MinimumImplication()
        self.aggregation: BinaryOperator = aggregation or MaximumSNorm()

    def infer(
        self,
        rule_base: RuleBase,
        interpretation: Interpretation,
        outputs: Mapping[str, LinguisticVariable],
    ) -> InferenceOutcome:
        activations: list[RuleActivation] = []
        contributions: dict[str, list[Contribution]] = {name: [] for name in outputs}
        for rule in rule_base:
            activation = self._activate(rule, interpretation)
            activations.append(activation)
            for consequent in rule.consequents:
                contributions[consequent.variable].append(
                    Contribution(rule.identifier, consequent, activation.strength)
                )
        distributions = {
            name: OutputDistribution(
                variable=outputs[name],
                contributions=tuple(contributions[name]),
                implication=self.implication,
                aggregation=self.aggregation,
            )
            for name in outputs
        }
        return InferenceOutcome(tuple(activations), distributions)

    def _activate(self, rule: Rule, interpretation: Interpretation) -> RuleActivation:
        truth = rule.antecedent.truth(interpretation, self.operators)
        atom_degrees = tuple(
            AtomEvaluation(atom, atom.truth(interpretation, self.operators))
            for atom in rule.antecedent.atoms()
        )
        return RuleActivation(
            rule=rule,
            antecedent_truth=truth,
            strength=rule.weight * truth,
            atom_degrees=atom_degrees,
        )
