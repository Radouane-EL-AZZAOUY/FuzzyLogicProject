"""Human-readable explanations of evaluations (French by default).

Explainability is the main advantage of a symbolic system over a black-box model:
every conclusion can be traced back to named rules and measured degrees. The
building blocks (:func:`explain_inputs`, :func:`explain_activations`,
:func:`explain_conclusions`) return lines so that applications can compose their
own layout; :func:`explain_result` is the default composition.
"""

from __future__ import annotations

from collections.abc import Iterable

from fuzzyengine.dsl.syntax import FRENCH, Syntax
from fuzzyengine.inference import RuleActivation
from fuzzyengine.observations import Degrees
from fuzzyengine.pipeline import PipelineResult
from fuzzyengine.system import EvaluationResult


def format_degrees(degrees: dict[str, float]) -> str:
    return ", ".join(f"{term}={degree:.2f}" for term, degree in degrees.items())


def indent(lines: Iterable[str], prefix: str = "  ") -> list[str]:
    return [f"{prefix}{line}" for line in lines]


def explain_inputs(result: EvaluationResult) -> list[str]:
    """One line per input: what was observed and its degrees in every term."""
    lines = []
    for name, degrees in result.fuzzified_inputs.items():
        observed = result.observations.get(name, result.inputs.get(name))
        if isinstance(observed, Degrees):
            lines.append(f"{name} : {format_degrees(degrees)} (conclusion de l'étape précédente)")
            continue
        shown = f"{observed:.4g}" if isinstance(observed, float) else str(observed)
        lines.append(f"{name} = {shown} -> {format_degrees(degrees)}")
    return lines


def explain_activations(
    activations: Iterable[RuleActivation],
    syntax: Syntax = FRENCH,
    limit: int | None = 5,
) -> list[str]:
    """One (or two, with description) line(s) per activation, in the given order."""
    lines: list[str] = []
    for index, activation in enumerate(activations):
        if limit is not None and index >= limit:
            break
        rule = activation.rule
        lines.append(
            f"- [{rule.identifier}] force={activation.strength:.2f} : {rule.render(syntax)}"
        )
        if rule.description:
            lines.append(f"    ({rule.description})")
    return lines


def explain_conclusions(result: EvaluationResult) -> list[str]:
    """One line per output: crisp value, best label and degrees in every term."""
    return [
        f"{name} = {value:.2f} ({result.label(name)} ; "
        f"{format_degrees(result.fuzzified_outputs[name])})"
        for name, value in result.outputs.items()
    ]


def explain_result(result: EvaluationResult, syntax: Syntax = FRENCH, limit: int | None = 5) -> str:
    lines = [f"Système « {result.system_name} »", "  Entrées :"]
    lines.extend(indent(explain_inputs(result), "    "))
    fired = result.fired_rules()
    if fired:
        lines.append(f"  Règles déclenchées ({len(fired)}/{len(result.activations)}), par force :")
        lines.extend(indent(explain_activations(fired, syntax, limit), "  "))
    else:
        lines.append("  Aucune règle déclenchée.")
    lines.append("  Conclusions :")
    lines.extend(indent(explain_conclusions(result), "    "))
    lines.extend(f"  [!] {warning}" for warning in result.warnings)
    return "\n".join(lines)


def explain_pipeline(result: PipelineResult, syntax: Syntax = FRENCH, limit: int | None = 3) -> str:
    return "\n\n".join(explain_result(stage, syntax, limit) for stage in result.stages)
