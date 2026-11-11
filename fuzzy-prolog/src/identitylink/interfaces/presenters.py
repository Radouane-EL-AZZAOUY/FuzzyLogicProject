"""Text and JSON presentations of linkage reports and metrics."""

from __future__ import annotations

from collections.abc import Sequence
from typing import Any

from identitylink.application.evaluate import Metrics
from identitylink.domain.match import LinkageReport, MatchCandidate
from identitylink.domain.record import PersonRecord


def record_to_dict(record: PersonRecord) -> dict[str, Any]:
    return {
        "id": record.identifier,
        "nom": record.last_name,
        "prenom": record.first_name,
        "date_naissance": str(record.birth),
        "ville": record.city,
        "telephone": record.phone,
        "email": record.email,
    }


def candidate_to_dict(candidate: MatchCandidate, explain: bool = False) -> dict[str, Any]:
    data: dict[str, Any] = {
        "a": candidate.left.identifier,
        "b": candidate.right.identifier,
        "degre": round(candidate.degree, 4),
        "regle": candidate.rule,
        "fiche_a": record_to_dict(candidate.left),
        "fiche_b": record_to_dict(candidate.right),
    }
    if explain:
        data["preuve"] = [
            {
                "niveau": s.level,
                "but": s.goal,
                "via": s.via,
                "degre": round(s.degree, 4),
                "cumul": round(s.cumulative, 4),
            }
            for s in candidate.proof.steps
        ]
    return data


def report_to_dict(report: LinkageReport, explain: bool = False) -> dict[str, Any]:
    return {
        "seuil": report.threshold,
        "fiches": report.records,
        "duree_s": round(report.seconds, 3),
        "candidats": len(report.candidates),
        "rapprochements": len(report.matches),
        "paires": [candidate_to_dict(c, explain) for c in report.candidates],
        "groupes": [list(g.identifiers) for g in report.groups],
    }


def metrics_to_dict(metrics: Sequence[Metrics]) -> list[dict[str, Any]]:
    return [
        {
            "seuil": m.threshold,
            "vrais_positifs": m.true_positives,
            "faux_positifs": m.false_positives,
            "faux_negatifs": m.false_negatives,
            "precision": round(m.precision, 4),
            "rappel": round(m.recall, 4),
            "f1": round(m.f1, 4),
        }
        for m in metrics
    ]


def _describe(record: PersonRecord) -> str:
    return f"{record.first_name} {record.last_name} ({record.birth}, {record.city or '?'})"


def format_report(report: LinkageReport, explain: bool = False, show_all: bool = False) -> str:
    title = f"Rapprochement d'identités — {report.records} fiches, seuil {report.threshold:.2f}"
    lines = [
        title,
        "=" * len(title),
        f"Paires candidates : {len(report.candidates)} | "
        f"rapprochements ≥ seuil : {len(report.matches)} | "
        f"groupes : {len(report.groups)} | {report.seconds:.2f} s",
        "",
        f"{'degré':>6}  {'A':<6} {'B':<6} {'fiche A':<42} {'fiche B':<42} règle",
    ]
    shown = report.candidates if show_all else report.matches
    for c in shown:
        rule = c.rule.split(":")[0].replace("clause ", "") if c.rule else "-"
        lines.append(
            f"{c.degree:>6.2f}  {c.left.identifier:<6} {c.right.identifier:<6} "
            f"{_describe(c.left)[:42]:<42} {_describe(c.right)[:42]:<42} {rule}"
        )
        if explain:
            lines.extend("        " + line for line in c.proof.explain().splitlines()[1:])
    if report.groups:
        lines.append("")
        lines.append("Groupes de doublons probables :")
        for group in report.groups:
            names = " | ".join(
                f"{m.identifier} {m.first_name} {m.last_name}" for m in group.members
            )
            lines.append(f"  - {names}")
    return "\n".join(lines)


def format_metrics(metrics: Sequence[Metrics]) -> str:
    lines = [
        f"{'seuil':>6} {'VP':>5} {'FP':>5} {'FN':>5} {'précision':>10} {'rappel':>8} {'F1':>7}"
    ]
    for m in metrics:
        lines.append(
            f"{m.threshold:>6.2f} {m.true_positives:>5} {m.false_positives:>5} "
            f"{m.false_negatives:>5} "
            f"{m.precision:>10.3f} {m.recall:>8.3f} {m.f1:>7.3f}"
        )
    return "\n".join(lines)
