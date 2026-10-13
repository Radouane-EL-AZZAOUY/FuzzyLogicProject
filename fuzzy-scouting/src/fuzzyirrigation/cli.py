"""Command-line interface ``fuzzyirrigation``."""

from __future__ import annotations

import argparse
import csv
import json
import sys
from collections.abc import Sequence
from pathlib import Path
from typing import Any

from fuzzyengine import FuzzyEngineError, explain_result
from fuzzyengine.console import ensure_utf8_console
from fuzzyirrigation import __version__
from fuzzyirrigation.advisor import IrrigationAdvisor
from fuzzyirrigation.domain import IrrigationDecision, SensorReading

REQUIRED_COLUMNS = ("humidite_sol", "temperature", "humidite_air")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="fuzzyirrigation", description="Contrôleur flou d'irrigation : durée d'arrosage."
    )
    parser.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    parser.add_argument("--knowledge", metavar="TOML", help="base de connaissances alternative")
    sub = parser.add_subparsers(dest="command", required=True)

    decide = sub.add_parser("decide", help="décider pour une mesure")
    decide.add_argument("--humidite-sol", type=float, required=True, help="%% d'humidité du sol")
    decide.add_argument("--temperature", type=float, required=True, help="°C")
    decide.add_argument("--humidite-air", type=float, required=True, help="%% d'humidité de l'air")
    decide.add_argument("--pluie-prevue", type=float, default=0.0, help="mm prévus sur 24 h")
    decide.add_argument("--explain", action="store_true")
    decide.add_argument("--json", action="store_true")

    batch = sub.add_parser("batch", help="décider pour un CSV de mesures")
    batch.add_argument(
        "csv",
        help="colonnes : parcelle, humidite_sol, temperature, humidite_air, pluie_prevue_mm",
    )
    batch.add_argument("--json", action="store_true")
    return parser


def decision_to_dict(decision: IrrigationDecision) -> dict[str, Any]:
    return {
        "parcelle": decision.reading.plot,
        "mesures": decision.reading.as_inputs(),
        "duree_minutes": round(decision.duration_minutes, 1),
        "label": decision.label,
        "arroser": decision.should_irrigate,
        "regles": [
            {"id": a.rule.identifier, "force": round(a.strength, 3)}
            for a in decision.result.fired_rules()
        ],
        "avertissements": list(decision.warnings),
    }


def format_decision(decision: IrrigationDecision, explain: bool = False) -> str:
    verdict = "arroser" if decision.should_irrigate else "ne pas arroser"
    lines = [
        f"{decision.reading.plot} : {verdict} — "
        f"{decision.duration_minutes:.0f} min ({decision.label})"
    ]
    if explain:
        lines.append(explain_result(decision.result))
    return "\n".join(lines)


def _read_readings(path: Path) -> list[SensorReading]:
    with path.open(encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        columns = set(reader.fieldnames or ())
        missing = [c for c in REQUIRED_COLUMNS if c not in columns]
        if missing:
            raise ValueError(f"{path} : colonne(s) manquante(s) : {', '.join(missing)}.")
        readings: list[SensorReading] = []
        for index, row in enumerate(reader, start=2):
            try:
                readings.append(
                    SensorReading(
                        humidite_sol=float(row["humidite_sol"]),
                        temperature=float(row["temperature"]),
                        humidite_air=float(row["humidite_air"]),
                        pluie_prevue_mm=float(row.get("pluie_prevue_mm") or 0.0),
                        plot=row.get("parcelle") or f"ligne {index}",
                    )
                )
            except ValueError as exc:
                raise ValueError(f"{path}, ligne {index} : {exc}") from exc
        return readings


def main(argv: Sequence[str] | None = None) -> int:
    ensure_utf8_console()
    args = build_parser().parse_args(argv)
    try:
        advisor = IrrigationAdvisor.from_file(args.knowledge)
        if args.command == "decide":
            reading = SensorReading(
                args.humidite_sol, args.temperature, args.humidite_air, args.pluie_prevue
            )
            decision = advisor.decide(reading)
            if args.json:
                print(json.dumps(decision_to_dict(decision), ensure_ascii=False, indent=2))
            else:
                print(format_decision(decision, args.explain))
            return 0
        decisions = advisor.decide_many(_read_readings(Path(args.csv)))
        if args.json:
            print(
                json.dumps([decision_to_dict(d) for d in decisions], ensure_ascii=False, indent=2)
            )
        else:
            print("\n".join(format_decision(d) for d in decisions))
        return 0
    except (FuzzyEngineError, ValueError, OSError) as exc:
        print(f"Erreur : {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":  # pragma: no cover
    sys.exit(main())
