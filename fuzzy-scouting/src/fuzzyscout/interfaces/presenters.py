"""Presentation: domain objects → plain dictionaries (JSON) and French text reports.

The CLI and the HTTP API share these functions so that both channels describe the
same evaluation in exactly the same way.
"""

from __future__ import annotations

from collections.abc import Iterable, Sequence
from typing import Any

from fuzzyengine import FRENCH, EvaluationResult, RuleActivation, Syntax
from fuzzyengine.explanation import (
    explain_activations,
    explain_conclusions,
    explain_inputs,
    indent,
)
from fuzzyscout.application.scouting_service import KnowledgeSummary
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


def stage_to_dict(stage: EvaluationResult, limit: int | None = 5) -> dict[str, Any]:
    fired = stage.fired_rules()
    if limit is not None:
        fired = fired[:limit]
    return {
        "systeme": stage.system_name,
        "entrees": {k: round(v, 4) for k, v in stage.inputs.items()},
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
