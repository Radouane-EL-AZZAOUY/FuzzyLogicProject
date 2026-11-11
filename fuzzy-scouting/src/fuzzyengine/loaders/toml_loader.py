"""Load fuzzy systems from declarative TOML knowledge bases.

File layout (see ``docs/04-moteur-fuzzyengine.md`` for the full specification)::

    [system]
    name = "technique_attaquant"
    description = "..."
    operators = "zadeh"        # optional: zadeh | probabilistic | lukasiewicz
    implication = "min"        # optional: min | product
    aggregation = "max"        # optional: max | probabilistic_sum | bounded_sum
    defuzzifier = "centroid"   # optional: centroid | bisector | mom
    resolution = 501           # optional

    [[inputs]]
    name = "buts_p90"
    universe = [0.0, 1.5]
    [inputs.terms]
    faible = { kind = "ramp_down", params = [0.15, 0.35] }

    [[outputs]]
    ...

    [[rules]]
    id = "T1"
    text = "SI buts_p90 EST eleve ALORS technique EST excellente"
    weight = 1.0
"""

from __future__ import annotations

import tomllib
from collections.abc import Iterable, Mapping
from pathlib import Path
from typing import Any

from fuzzyengine.defuzzification import defuzzifier_from_name
from fuzzyengine.dsl.parser import parse_rule
from fuzzyengine.exceptions import FuzzyEngineError, KnowledgeBaseError
from fuzzyengine.inference import MamdaniInference
from fuzzyengine.membership import membership_from_spec
from fuzzyengine.operators import (
    aggregation_from_name,
    implication_from_name,
    operators_from_name,
)
from fuzzyengine.pipeline import FuzzyPipeline
from fuzzyengine.rules import Rule, RuleBase
from fuzzyengine.system import FuzzySystem
from fuzzyengine.universe import Universe
from fuzzyengine.variables import FuzzySet, LinguisticVariable


class _Spec:
    """Typed accessor over a TOML table with precise error messages."""

    def __init__(self, data: Mapping[str, Any], context: str) -> None:
        self.data = data
        self.context = context

    def fail(self, message: str) -> KnowledgeBaseError:
        return KnowledgeBaseError(f"[{self.context}] {message}")

    def required(self, key: str, expected: type | tuple[type, ...]) -> Any:
        if key not in self.data:
            raise self.fail(f"clé obligatoire manquante : '{key}'.")
        return self.typed(key, expected)

    def optional(self, key: str, expected: type | tuple[type, ...], default: Any) -> Any:
        if key not in self.data:
            return default
        return self.typed(key, expected)

    def typed(self, key: str, expected: type | tuple[type, ...]) -> Any:
        value = self.data[key]
        if isinstance(value, bool) or not isinstance(value, expected):
            names = (
                expected.__name__
                if isinstance(expected, type)
                else " ou ".join(t.__name__ for t in expected)
            )
            raise self.fail(f"'{key}' doit être de type {names} (reçu {type(value).__name__}).")
        return value

    def child(self, key: str, data: Mapping[str, Any]) -> _Spec:
        return _Spec(data, f"{self.context}.{key}")


def _build_variable(spec: _Spec) -> LinguisticVariable:
    name = spec.required("name", str)
    spec = _Spec(spec.data, f"{spec.context}({name})")
    bounds = spec.required("universe", list)
    if len(bounds) != 2 or not all(isinstance(b, int | float) for b in bounds):
        raise spec.fail("'universe' doit être une liste de deux nombres [min, max].")
    terms_table = spec.required("terms", dict)
    if not terms_table:
        raise spec.fail("'terms' ne peut pas être vide.")
    terms: list[FuzzySet] = []
    for label, definition in terms_table.items():
        if not isinstance(definition, dict):
            raise spec.fail(f"le terme '{label}' doit être une table {{ kind, params }}.")
        term_spec = spec.child(f"terms.{label}", definition)
        kind = term_spec.required("kind", str)
        params = term_spec.required("params", list)
        try:
            terms.append(FuzzySet(label, membership_from_spec(kind, params)))
        except FuzzyEngineError as exc:
            raise term_spec.fail(str(exc)) from exc
    try:
        return LinguisticVariable(
            name=name,
            universe=Universe(float(bounds[0]), float(bounds[1])),
            terms=tuple(terms),
            description=spec.optional("description", str, ""),
            unit=spec.optional("unit", str, ""),
        )
    except FuzzyEngineError as exc:
        raise spec.fail(str(exc)) from exc


Library = Mapping[str, LinguisticVariable]


def _resolve_reference(spec: _Spec, library: Library | None) -> LinguisticVariable:
    reference = spec.required("ref", str)
    if library is None or reference not in library:
        known = ", ".join(sorted(library)) if library else "aucune"
        raise spec.fail(
            f"variable partagée inconnue '{reference}' (bibliothèque disponible : {known})."
        )
    return library[reference]


def _build_variables(
    root: _Spec, key: str, library: Library | None
) -> dict[str, LinguisticVariable]:
    entries = root.optional(key, list, [])
    variables: dict[str, LinguisticVariable] = {}
    for index, entry in enumerate(entries):
        if not isinstance(entry, dict):
            raise root.fail(f"'{key}[{index}]' doit être une table.")
        spec = root.child(f"{key}[{index}]", entry)
        variable = _resolve_reference(spec, library) if "ref" in entry else _build_variable(spec)
        if variable.name in variables:
            raise root.fail(f"variable '{variable.name}' déclarée deux fois dans '{key}'.")
        variables[variable.name] = variable
    return variables


def load_library_from_dict(
    data: Mapping[str, Any], source: str = "<dict>"
) -> dict[str, LinguisticVariable]:
    """Build a library of shared variables from a ``[[variables]]`` document."""
    root = _Spec(data, source)
    return _build_variables(root, "variables", None)


def load_library(path: str | Path) -> dict[str, LinguisticVariable]:
    """Read a library of shared linguistic variables (``[[variables]]`` tables)."""
    file_path = Path(path)
    return load_library_from_dict(_read_toml(file_path), source=str(file_path))


def _build_rules(root: _Spec) -> RuleBase:
    entries = root.optional("rules", list, [])
    rules: list[Rule] = []
    for index, entry in enumerate(entries):
        if not isinstance(entry, dict):
            raise root.fail(f"'rules[{index}]' doit être une table.")
        spec = root.child(f"rules[{index}]", entry)
        identifier = spec.optional("id", (str, int), f"R{index + 1}")
        text = spec.required("text", str)
        weight = float(spec.optional("weight", (int, float), 1.0))
        description = spec.optional("description", str, "")
        try:
            rules.append(parse_rule(text, str(identifier), weight, description))
        except FuzzyEngineError as exc:
            raise spec.fail(f"règle '{identifier}' invalide : {exc}") from exc
    return RuleBase(tuple(rules))


def load_system_from_dict(
    data: Mapping[str, Any], source: str = "<dict>", library: Library | None = None
) -> FuzzySystem:
    """Build a :class:`FuzzySystem` from an already-parsed TOML document.

    ``library`` holds shared variables that ``[[inputs]]``/``[[outputs]]`` entries may
    reference with ``ref = "name"`` instead of an inline definition.
    """
    root = _Spec(data, source)
    system_spec = root.child("system", root.required("system", dict))
    name = system_spec.required("name", str)
    try:
        inference = MamdaniInference(
            operators=operators_from_name(system_spec.optional("operators", str, "zadeh")),
            implication=implication_from_name(system_spec.optional("implication", str, "min")),
            aggregation=aggregation_from_name(system_spec.optional("aggregation", str, "max")),
        )
        defuzzifier = defuzzifier_from_name(
            system_spec.optional("defuzzifier", str, "centroid"),
            system_spec.optional("resolution", int, None),
        )
        return FuzzySystem(
            name=name,
            description=system_spec.optional("description", str, ""),
            inputs=_build_variables(root, "inputs", library),
            outputs=_build_variables(root, "outputs", library),
            rule_base=_build_rules(root),
            inference=inference,
            defuzzifier=defuzzifier,
        )
    except KnowledgeBaseError:
        raise
    except FuzzyEngineError as exc:
        raise root.fail(str(exc)) from exc


def _read_toml(file_path: Path) -> dict[str, Any]:
    try:
        return tomllib.loads(file_path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise KnowledgeBaseError(f"Base de connaissances introuvable : {file_path}") from exc
    except (OSError, UnicodeDecodeError) as exc:
        raise KnowledgeBaseError(f"Impossible de lire {file_path} : {exc}") from exc
    except tomllib.TOMLDecodeError as exc:
        raise KnowledgeBaseError(f"[{file_path}] TOML invalide : {exc}") from exc


def load_system(path: str | Path, library: Library | None = None) -> FuzzySystem:
    """Read and build a fuzzy system from a TOML file."""
    file_path = Path(path)
    return load_system_from_dict(_read_toml(file_path), source=str(file_path), library=library)


def load_pipeline(
    name: str,
    paths: Iterable[str | Path],
    description: str = "",
    library: Library | None = None,
    chaining: str = "crisp",
) -> FuzzyPipeline:
    """Chain the systems read from ``paths`` (in order) into a pipeline.

    ``chaining`` is ``"crisp"`` or ``"fuzzy"`` (see :mod:`fuzzyengine.pipeline`).
    """
    try:
        return FuzzyPipeline(
            name, tuple(load_system(p, library) for p in paths), description, chaining
        )
    except KnowledgeBaseError:
        raise
    except FuzzyEngineError as exc:
        raise KnowledgeBaseError(f"[pipeline {name}] {exc}") from exc
