"""Presentation: domain objects → plain dictionaries (JSON) and French text reports.

The CLI and the HTTP API share these functions so that both channels describe the
same evaluation in exactly the same way.
"""

from __future__ import annotations

from collections.abc import Iterable, Sequence
from typing import Any

from fuzzyengine import (
    FRENCH,
    Category,
    Degrees,
    EvaluationResult,
    FuzzyPipeline,
    Interval,
    LinguisticVariable,
    Observation,
    Rule,
    RuleActivation,
    Syntax,
)
from fuzzyengine.explanation import (
    explain_activations,
    explain_conclusions,
    explain_inputs,
    indent,
)
from fuzzyscout.application.scouting_service import KnowledgeSummary
from fuzzyscout.domain.command import HIGHEST_LEVEL, CommandEvaluation, CommandRanking
from fuzzyscout.domain.evaluation import PlayerEvaluation, RankingReport
from fuzzyscout.domain.player import Player
from fuzzyscout.domain.position import Position

SCORE_ORDER = ("technique", "physique", "profil", "aptitude")

# --- dictionaries (JSON) ----------------------------------------------------------


def player_to_dict(player: Player) -> dict[str, Any]:
    return {
        "id": player.identifier,
        "nom": player.name,
        "club": player.club,
        "nationalite": player.nationality,
        "poste": player.position,
        "attributs": dict(player.attributes),
    }


def position_to_dict(position: Position) -> dict[str, Any]:
    return {
        "code": position.code,
        "libelle": position.label,
        "description": position.description,
        "etapes": list(position.stages),
    }


def activation_to_dict(activation: RuleActivation, syntax: Syntax = FRENCH) -> dict[str, Any]:
    rule = activation.rule
    return {
        "id": rule.identifier,
        "force": round(activation.strength, 4),
        "verite_antecedent": round(activation.antecedent_truth, 4),
        "regle": rule.render(syntax),
        "description": rule.description,
        "atomes": [
            {"atome": a.atom.render(syntax), "degre": round(a.degree, 4)}
            for a in activation.atom_degrees
        ],
    }


def observation_to_dict(observation: Observation) -> dict[str, Any]:
    """An observation with its kind: ``valeur``, ``intervalle``, ``categorie`` or ``degres``."""
    if isinstance(observation, Interval):
        return {
            "type": "intervalle",
            "min": observation.lower,
            "max": observation.upper,
            "texte": str(observation),
        }
    if isinstance(observation, Category):
        return {"type": "categorie", "terme": observation.term, "texte": observation.term}
    if isinstance(observation, Degrees):
        degrees = {term: round(degree, 4) for term, degree in observation.degrees.items()}
        return {"type": "degres", "degres": degrees, "texte": str(observation)}
    return {"type": "valeur", "valeur": observation, "texte": f"{observation:g}"}


def stage_to_dict(stage: EvaluationResult, limit: int | None = 5) -> dict[str, Any]:
    fired = stage.fired_rules()
    if limit is not None:
        fired = fired[:limit]
    return {
        "systeme": stage.system_name,
        "entrees": {k: round(v, 4) for k, v in stage.inputs.items()},
        "observations": {k: observation_to_dict(v) for k, v in stage.observations.items()},
        "conclusions": {
            k: {t: round(d, 4) for t, d in terms.items()} for k, terms in stage.conclusions.items()
        },
        "entrees_floues": {
            k: {t: round(d, 4) for t, d in terms.items()}
            for k, terms in stage.fuzzified_inputs.items()
        },
        "regles_declenchees": [activation_to_dict(a) for a in fired],
        "nb_regles_declenchees": len(stage.fired_rules()),
        "nb_regles": len(stage.activations),
        "sorties": {k: round(v, 4) for k, v in stage.outputs.items()},
        "sorties_floues": {
            k: {t: round(d, 4) for t, d in terms.items()}
            for k, terms in stage.fuzzified_outputs.items()
        },
        "avertissements": list(stage.warnings),
    }


def evaluation_to_dict(evaluation: PlayerEvaluation, include_trace: bool = False) -> dict[str, Any]:
    data: dict[str, Any] = {
        "joueur": player_to_dict(evaluation.player),
        "poste": evaluation.position.code,
        "aptitude": round(evaluation.aptitude, 2),
        "aptitude_label": evaluation.aptitude_label,
        "scores": {k: round(v, 2) for k, v in evaluation.scores.items()},
        "labels": evaluation.labels,
        "avertissements": list(evaluation.warnings),
    }
    if include_trace:
        data["etapes"] = [stage_to_dict(stage) for stage in evaluation.result.stages]
    return data


def ranking_to_dict(report: RankingReport, include_trace: bool = False) -> dict[str, Any]:
    return {
        "poste": position_to_dict(report.position),
        "filtres": report.filters.describe(),
        "candidats": report.candidates,
        "classes": report.ranked,
        "classement": [
            {"rang": entry.rank, **evaluation_to_dict(entry.evaluation, include_trace)}
            for entry in report.entries
        ],
        "exclus": [
            {"id": s.player.identifier, "nom": s.player.name, "raison": s.reason}
            for s in report.skipped
        ],
    }


def knowledge_to_dict(summaries: Iterable[KnowledgeSummary]) -> list[dict[str, Any]]:
    return [
        {
            "poste": s.position.code,
            "entrees_requises": list(s.required_inputs),
            "nb_regles": s.rules,
            "etapes": [
                {
                    "nom": st.name,
                    "entrees": list(st.inputs),
                    "sorties": list(st.outputs),
                    "regles": st.rules,
                }
                for st in s.stages
            ],
        }
        for s in summaries
    ]


def variable_to_dict(variable: LinguisticVariable, resolution: int = 81) -> dict[str, Any]:
    """A linguistic variable with each term's membership curve sampled for plotting.

    The curve is sampled server-side (regular grid + the shape's own parameters, which
    are the breakpoints of piecewise-linear shapes) so that clients never have to
    re-implement membership functions.
    """
    universe = variable.universe
    grid = universe.grid(resolution)
    terms = []
    for term in variable.terms:
        breakpoints = [p for p in term.membership.parameters() if universe.contains(p)]
        xs = sorted({round(x, 6) for x in (*grid, *breakpoints)})
        terms.append(
            {
                "label": term.label,
                "forme": str(term.membership),
                "points": [[x, round(term.degree(x), 4)] for x in xs],
            }
        )
    return {
        "nom": variable.name,
        "description": variable.description,
        "unite": variable.unit,
        "univers": [universe.lower, universe.upper],
        "termes": terms,
    }


def rule_to_dict(rule: Rule, syntax: Syntax = FRENCH) -> dict[str, Any]:
    return {
        "id": rule.identifier,
        "regle": rule.render(syntax),
        "description": rule.description,
        "poids": rule.weight,
    }


def pipeline_to_dict(position: Position, pipeline: FuzzyPipeline) -> dict[str, Any]:
    """The full knowledge of one position: every stage with its readable rules."""
    return {
        "poste": position_to_dict(position),
        "entrees_requises": list(pipeline.required_inputs),
        "etapes": [
            {
                "nom": stage.name,
                "description": stage.description,
                "entrees": list(stage.input_names),
                "sorties": list(stage.output_names),
                "regles": [rule_to_dict(rule) for rule in stage.rule_base],
            }
            for stage in pipeline.stages
        ],
    }


def command_to_dict(pipeline: FuzzyPipeline) -> dict[str, Any]:
    """The whole « commande Scout » system: stages, readable rules and variables."""
    variables: dict[str, LinguisticVariable] = {}
    for stage in pipeline.stages:
        variables.update(stage.inputs)
        variables.update(stage.outputs)
    final = pipeline.final_outputs[0]
    return {
        "code": pipeline.name,
        "libelle": pipeline.description,
        "chainage": pipeline.chaining,
        "niveaux": HIGHEST_LEVEL,
        "sortie": final,
        "variables_deduites": [name for name in pipeline.produced_outputs if name != final],
        "entrees_requises": list(pipeline.required_inputs),
        "etapes": [
            {
                "nom": stage.name,
                "description": stage.description,
                "entrees": list(stage.input_names),
                "sorties": list(stage.output_names),
                "regles": [rule_to_dict(rule) for rule in stage.rule_base],
            }
            for stage in pipeline.stages
        ],
        "variables": [variable_to_dict(variable) for variable in variables.values()],
    }


def command_evaluation_to_dict(
    evaluation: CommandEvaluation, include_trace: bool = False
) -> dict[str, Any]:
    player = evaluation.player
    conclusions = evaluation.conclusions
    data: dict[str, Any] = {
        "joueur": {
            "id": player.identifier,
            "nom": player.name,
            "club": player.club,
            "nationalite": player.nationality,
            "poste": player.position,
        },
        "niveau": evaluation.level,
        "niveau_valeur": round(evaluation.level_value, 2),
        "variables": {
            name: {
                "valeur": round(value, 1),
                "label": evaluation.labels[name],
                "degres": {t: round(d, 4) for t, d in conclusions[name].items()},
            }
            for name, value in evaluation.deduced.items()
        },
        "degres_niveau": {
            term: round(degree, 4) for term, degree in conclusions[evaluation.final_output].items()
        },
        "observations": {
            name: observation_to_dict(obs) for name, obs in evaluation.observations.items()
        },
        "avertissements": list(evaluation.warnings),
    }
    if include_trace:
        data["etapes"] = [stage_to_dict(stage, limit=None) for stage in evaluation.result.stages]
    return data


def command_ranking_to_dict(report: CommandRanking) -> dict[str, Any]:
    return {
        "poste": position_to_dict(report.position) if report.position else None,
        "candidats": report.candidates,
        "classes": len(report.entries),
        "classement": [
            {"rang": rank, **command_evaluation_to_dict(evaluation)}
            for rank, evaluation in enumerate(report.entries, start=1)
        ],
        "exclus": [
            {"id": s.player.identifier, "nom": s.player.name, "raison": s.reason}
            for s in report.skipped
        ],
    }


# --- text ---------------------------------------------------------------------


def _fmt(value: float | None, digits: int = 1) -> str:
    return "-" if value is None else f"{value:.{digits}f}"


def _scores_line(evaluation: PlayerEvaluation) -> str:
    parts = []
    for name in SCORE_ORDER:
        if name in evaluation.scores:
            parts.append(f"{name}={evaluation.scores[name]:.1f} ({evaluation.labels[name]})")
    return " | ".join(parts)


def format_positions(positions: Sequence[Position]) -> str:
    width = max(len(p.code) for p in positions) if positions else 10
    lines = ["Postes disponibles :"]
    for position in positions:
        lines.append(f"  {position.code:<{width}}  {position.label} — {position.description}")
    return "\n".join(lines)


def format_evaluation(evaluation: PlayerEvaluation, explain: bool = False, limit: int = 3) -> str:
    player = evaluation.player
    header = (
        f"{player.name} [{player.identifier}] — {player.club or 'club ?'}"
        f" — {player.position or 'poste ?'}, {_fmt(player.age, 0)} ans"
    )
    lines = [
        header,
        f"Poste évalué : {evaluation.position.label} ({evaluation.position.code})",
        f"Aptitude : {evaluation.aptitude:.1f}/100 ({evaluation.aptitude_label})",
        f"Détail : {_scores_line(evaluation)}",
    ]
    if explain:
        lines.append("Pourquoi :")
        for stage in evaluation.result.stages:
            lines.append(f"  Étape « {stage.system_name} »")
            lines.extend(indent(explain_inputs(stage), "    "))
            fired = stage.fired_rules()
            if not fired:
                lines.append("    (aucune règle déclenchée)")
            lines.extend(indent(explain_activations(fired, FRENCH, limit), "    "))
            lines.extend(indent(explain_conclusions(stage), "    => "))
    for warning in evaluation.warnings:
        lines.append(f"[!] {warning}")
    return "\n".join(lines)


def format_ranking(report: RankingReport, explain: bool = False) -> str:
    position = report.position
    title = f"Classement — {position.label} ({position.code})"
    filters = ", ".join(report.filters.describe()) or "aucun"
    lines = [
        title,
        "=" * len(title),
        f"Candidats : {report.candidates} | classés : {report.ranked} | "
        f"exclus : {len(report.skipped)}",
        f"Filtres : {filters}",
        "",
        f"{'#':>3}  {'id':<6} {'nom':<22} {'club':<22} {'poste':<18} {'âge':>4} {'M€':>6} "
        f"{'apt.':>6}  {'label':<10} {'tech':>5} {'phys':>5} {'prof':>5}",
    ]
    for entry in report.entries:
        e = entry.evaluation
        p = e.player
        s = e.scores
        lines.append(
            f"{entry.rank:>3}  {p.identifier:<6} {p.name[:22]:<22} {p.club[:22]:<22} "
            f"{p.position[:18]:<18} {_fmt(p.age, 0):>4} {_fmt(p.market_value):>6} "
            f"{e.aptitude:>6.1f}  {e.aptitude_label:<10} {_fmt(s.get('technique')):>5} "
            f"{_fmt(s.get('physique')):>5} {_fmt(s.get('profil')):>5}"
        )
    if report.skipped:
        lines.append("")
        lines.append("Exclus :")
        for skipped in report.skipped:
            lines.append(
                f"  - {skipped.player.name} [{skipped.player.identifier}] : {skipped.reason}"
            )
    if explain:
        for entry in report.entries:
            lines.append("")
            lines.append(f"--- #{entry.rank} ---")
            lines.append(format_evaluation(entry.evaluation, explain=True))
    return "\n".join(lines)


def format_knowledge(summaries: Sequence[KnowledgeSummary]) -> str:
    lines = ["Bases de connaissances valides :"]
    for summary in summaries:
        lines.append(
            f"  {summary.position.code} : {len(summary.stages)} étape(s), "
            f"{summary.rules} règle(s), entrées requises : {', '.join(summary.required_inputs)}"
        )
        for stage in summary.stages:
            lines.append(
                f"      - {stage.name} : {len(stage.inputs)} entrée(s) -> "
                f"{', '.join(stage.outputs)} ({stage.rules} règles)"
            )
    return "\n".join(lines)


def _deduced_line(evaluation: CommandEvaluation) -> str:
    return " | ".join(
        f"{name}={value:.0f} ({evaluation.labels[name]})"
        for name, value in evaluation.deduced.items()
    )


def format_command_evaluation(evaluation: CommandEvaluation, explain: bool = False) -> str:
    player = evaluation.player
    identity = f"{player.name} [{player.identifier}]"
    if player.position:
        identity += f" — {player.position}"
    lines = [
        identity,
        f"Niveau : {evaluation.level} / {HIGHEST_LEVEL} (valeur {evaluation.level_value:.2f})",
        f"Variables déduites : {_deduced_line(evaluation)}",
    ]
    if explain:
        lines.append("Pourquoi :")
        for stage in evaluation.result.stages:
            lines.append(f"  Étape « {stage.system_name} »")
            lines.extend(indent(explain_inputs(stage), "    "))
            lines.extend(indent(explain_activations(stage.fired_rules(), FRENCH, 3), "    "))
            for name, degrees in stage.conclusions.items():
                concluded = ", ".join(f"{t}={d:.2f}" for t, d in degrees.items() if d > 0)
                lines.append(f"    => {name} : {concluded or 'aucune règle déclenchée'}")
    for warning in evaluation.warnings:
        lines.append(f"[!] {warning}")
    return "\n".join(lines)


def format_command_ranking(report: CommandRanking) -> str:
    scope = f"{report.position.label} ({report.position.code})" if report.position else "tous"
    title = f"Commande Scout — joueurs : {scope}"
    lines = [
        title,
        "=" * len(title),
        f"Candidats : {report.candidates} | classés : {len(report.entries)} | "
        f"exclus : {len(report.skipped)}",
        "",
        f"{'#':>3}  {'id':<6} {'nom':<22} {'poste':<18} {'niveau':>6} {'valeur':>6}  "
        f"{'vitesse':<13} {'accélération':<13} {'tacle':<13}",
    ]
    for rank, e in enumerate(report.entries, start=1):
        p = e.player
        cells = [f"{e.deduced[n]:>3.0f} {e.labels[n]:<9}" for n in e.deduced]
        lines.append(
            f"{rank:>3}  {p.identifier:<6} {p.name[:22]:<22} {p.position[:18]:<18} "
            f"{e.level:>6} {e.level_value:>6.2f}  {' '.join(cells)}"
        )
    if report.skipped:
        lines.append("")
        lines.append("Exclus :")
        for skipped in report.skipped:
            lines.append(
                f"  - {skipped.player.name} [{skipped.player.identifier}] : {skipped.reason}"
            )
    return "\n".join(lines)
