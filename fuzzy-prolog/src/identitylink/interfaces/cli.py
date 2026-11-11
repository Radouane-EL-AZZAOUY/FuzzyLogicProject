"""Command-line interface ``identitylink``.

identitylink dedupe [fiches.csv] [--threshold 0.7] [--explain] [--all] [--json]
identitylink evaluate [fiches.csv] [--truth verite.csv] [--thresholds 0.5,0.6,...]
identitylink query [fiches.csv] "meme_personne(p0001, X)." [--explain]
identitylink generate --out DIR [--persons 150] [--seed 7]
"""

from __future__ import annotations

import argparse
import json
import sys
from collections.abc import Sequence
from pathlib import Path

from fuzzyprolog import FuzzyPrologError
from fuzzyprolog.cli import ensure_utf8_console
from fuzzyprolog.tnorms import tnorm_from_name
from identitylink import __version__
from identitylink.application.deduplicate import Deduplicator
from identitylink.application.evaluate import false_pairs, sweep, truth_pairs
from identitylink.infrastructure.csv_repository import DataError, read_records, read_truth
from identitylink.infrastructure.knowledge import (
    PackagedKnowledge,
    default_records_csv,
    default_truth_csv,
)
from identitylink.interfaces import presenters

DEFAULT_THRESHOLDS = (0.5, 0.6, 0.7, 0.8, 0.9, 1.0)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="identitylink", description="Rapprochement d'identités par Prolog flou."
    )
    parser.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    parser.add_argument("--rules", metavar="PL", help="fichier de règles alternatif")
    parser.add_argument("--similarities", metavar="PL", help="fichier de similarités alternatif")
    parser.add_argument(
        "--lambda-cut",
        type=float,
        default=None,
        help="seuil λ de coupure (défaut : directive des règles)",
    )
    parser.add_argument("--tnorm", default=None, help="min | product | lukasiewicz")
    sub = parser.add_subparsers(dest="command", required=True)

    dedupe = sub.add_parser("dedupe", help="détecter les doublons d'un fichier de fiches")
    dedupe.add_argument("records", nargs="?", help="CSV des fiches (défaut : jeu d'exemple)")
    dedupe.add_argument(
        "--threshold", type=float, default=0.7, help="degré minimal d'un rapprochement"
    )
    dedupe.add_argument(
        "--explain", action="store_true", help="afficher la preuve de chaque rapprochement"
    )
    dedupe.add_argument(
        "--all", action="store_true", help="afficher aussi les paires sous le seuil"
    )
    dedupe.add_argument("--json", action="store_true")

    evaluate = sub.add_parser(
        "evaluate", help="mesurer précision / rappel / F1 contre une vérité terrain"
    )
    evaluate.add_argument("records", nargs="?")
    evaluate.add_argument("--truth", help="CSV id,personne (défaut : vérité du jeu d'exemple)")
    evaluate.add_argument("--thresholds", default=",".join(str(t) for t in DEFAULT_THRESHOLDS))
    evaluate.add_argument(
        "--errors", action="store_true", help="lister faux positifs / faux négatifs au seuil 0.7"
    )
    evaluate.add_argument("--json", action="store_true")

    query = sub.add_parser(
        "query", help="interroger la base de connaissances construite sur les fiches"
    )
    query.add_argument("records", nargs="?")
    query.add_argument("goal", help='requête Prolog, ex. "meme_personne(p0001, X)."')
    query.add_argument("--explain", action="store_true")
    query.add_argument("--max", type=int, default=50)

    generate = sub.add_parser("generate", help="générer un jeu de données synthétique")
    generate.add_argument("--out", required=True, help="répertoire de sortie")
    generate.add_argument("--persons", type=int, default=150)
    generate.add_argument("--seed", type=int, default=7)
    return parser


def _run(args: argparse.Namespace) -> int:
    if args.command == "generate":
        from identitylink.infrastructure.synthetic import generate_dataset

        records_path, truth_path, count = generate_dataset(Path(args.out), args.persons, args.seed)
        print(f"{count} fiches écrites dans {records_path} (vérité : {truth_path})")
        return 0
    knowledge = PackagedKnowledge(args.rules, args.similarities)
    records = read_records(args.records or default_records_csv())
    deduplicator = Deduplicator(
        knowledge,
        lambda_cut=args.lambda_cut,
        tnorm=tnorm_from_name(args.tnorm) if args.tnorm else None,
    )
    if args.command == "query":
        engine = deduplicator.engine_for(records)
        count = 0
        for solution in engine.query(args.goal, limit=args.max):
            count += 1
            print(solution.explain() if args.explain else str(solution))
        if count == 0:
            print("non.")
        return 0
    if args.command == "dedupe":
        report = deduplicator.run(records, args.threshold)
        if args.json:
            print(
                json.dumps(
                    presenters.report_to_dict(report, args.explain), ensure_ascii=False, indent=2
                )
            )
        else:
            print(presenters.format_report(report, args.explain, args.all))
        return 0
    if args.command == "evaluate":
        truth = truth_pairs(read_truth(args.truth or default_truth_csv()))
        thresholds = [float(t) for t in args.thresholds.split(",") if t.strip()]
        report = deduplicator.run(records, min(thresholds) if thresholds else 0.7)
        metrics = sweep(report, truth, thresholds)
        if args.json:
            print(json.dumps(presenters.metrics_to_dict(metrics), ensure_ascii=False, indent=2))
        else:
            print(
                f"{report.records} fiches, {len(truth)} paires vraies, "
                f"{len(report.candidates)} paires candidates"
            )
            print(presenters.format_metrics(metrics))
            if args.errors:
                at_07 = report if report.threshold == 0.7 else deduplicator.run(records, 0.7)
                fps, fns = false_pairs(at_07, truth)
                print(f"\nFaux positifs ({len(fps)}) : {fps}\nFaux négatifs ({len(fns)}) : {fns}")
        return 0
    raise AssertionError(args.command)  # pragma: no cover


def main(argv: Sequence[str] | None = None) -> int:
    ensure_utf8_console()
    args = build_parser().parse_args(argv)
    try:
        return _run(args)
    except (DataError, FuzzyPrologError, ValueError, OSError) as exc:
        print(f"Erreur : {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":  # pragma: no cover
    sys.exit(main())
