"""Fuzzy production rules and rule bases.

A rule ``IF antecedent THEN out IS term`` is the graded counterpart of a Horn clause
``tête :- c1, c2, …, cn`` (course, § Prolog): the head holds *to the degree* to which
the body holds. A :class:`RuleBase` is the set of axioms of our formal system.
"""

from __future__ import annotations

from collections.abc import Iterator, Mapping
from dataclasses import dataclass, field

from fuzzyengine.dsl.syntax import ENGLISH, Syntax
from fuzzyengine.exceptions import KnowledgeBaseError
from fuzzyengine.formulas import Formula
from fuzzyengine.variables import LinguisticVariable


@dataclass(frozen=True, slots=True)
class Consequent:
    """``variable IS term`` on the right-hand side of a rule."""

    variable: str
    term: str

    def render(self, syntax: Syntax = ENGLISH) -> str:
        return f"{self.variable} {syntax.IS} {self.term}"

    def __str__(self) -> str:
        return self.render(ENGLISH)


@dataclass(frozen=True, slots=True)
class Rule:
    identifier: str
    antecedent: Formula
    consequents: tuple[Consequent, ...]
    weight: float = 1.0
    description: str = ""

    def __post_init__(self) -> None:
        if not self.identifier or not self.identifier.strip():
            raise KnowledgeBaseError("Une règle doit avoir un identifiant non vide.")
        if not self.consequents:
            raise KnowledgeBaseError(f"La règle '{self.identifier}' n'a aucune conclusion.")
        if not 0.0 < self.weight <= 1.0:
            raise KnowledgeBaseError(
                f"Le poids de la règle '{self.identifier}' doit être dans ]0, 1] "
                f"(reçu {self.weight})."
            )

    def render(self, syntax: Syntax = ENGLISH) -> str:
        head = f" {syntax.AND} ".join(c.render(syntax) for c in self.consequents)
        return f"{syntax.IF} {self.antecedent.render(syntax)} {syntax.THEN} {head}"

    def __str__(self) -> str:
        return self.render(ENGLISH)


@dataclass(frozen=True, slots=True)
class RuleBase:
    """Ordered, duplicate-free collection of rules."""

    rules: tuple[Rule, ...]
    _index: dict[str, Rule] = field(init=False, repr=False, compare=False)

    def __post_init__(self) -> None:
        index: dict[str, Rule] = {}
        for rule in self.rules:
            if rule.identifier in index:
                raise KnowledgeBaseError(f"Identifiant de règle dupliqué : '{rule.identifier}'.")
            index[rule.identifier] = rule
        object.__setattr__(self, "_index", index)

    def __iter__(self) -> Iterator[Rule]:
        return iter(self.rules)

    def __len__(self) -> int:
        return len(self.rules)

    def get(self, identifier: str) -> Rule:
        try:
            return self._index[identifier]
        except KeyError as exc:
            raise KnowledgeBaseError(f"Règle inconnue : '{identifier}'.") from exc

    def validate(
        self,
        inputs: Mapping[str, LinguisticVariable],
        outputs: Mapping[str, LinguisticVariable],
    ) -> None:
        """Check every atom/consequent refers to a declared variable and term.

        Raises :class:`KnowledgeBaseError` describing the first inconsistency found,
        so that knowledge-base authors get a precise diagnostic at load time.
        """
        for rule in self.rules:
            for atom in rule.antecedent.atoms():
                _check_reference(inputs, atom.variable, atom.term, rule.identifier, "d'entrée")
            for consequent in rule.consequents:
                _check_reference(
                    outputs, consequent.variable, consequent.term, rule.identifier, "de sortie"
                )


def _check_reference(
    variables: Mapping[str, LinguisticVariable],
    variable_name: str,
    term: str,
    rule_identifier: str,
    role: str,
) -> None:
    variable = variables.get(variable_name)
    if variable is None:
        raise KnowledgeBaseError(
            f"Règle '{rule_identifier}' : variable {role} inconnue '{variable_name}' "
            f"(variables {role} déclarées : {', '.join(variables) or 'aucune'})."
        )
    if not variable.has_term(term):
        raise KnowledgeBaseError(
            f"Règle '{rule_identifier}' : terme inconnu '{term}' pour la variable {role} "
            f"'{variable_name}' (termes : {', '.join(variable.labels)})."
        )
