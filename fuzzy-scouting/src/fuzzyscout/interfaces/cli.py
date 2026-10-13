"""Command-line interface ``fuzzyscout``.

Exit codes: 0 success, 1 domain/knowledge/data error (message on stderr), 2 usage error.
"""

from __future__ import annotations

import argparse
import json
import logging
import sys
from collections.abc import Sequence
from typing import Any

from fuzzyengine import FuzzyEngineError
from fuzzyengine.console import ensure_utf8_console
from fuzzyscout import __version__
from fuzzyscout.application.rank_players import RankingRequest
from fuzzyscout.application.scouting_service import ScoutingService
from fuzzyscout.bootstrap import build_service, configure_logging
from fuzzyscout.config import Settings
from fuzzyscout.domain.errors import ScoutingError
from fuzzyscout.domain.filters import RankingFilters
from fuzzyscout.interfaces import presenters

logger = logging.getLogger(__name__)


def _parse_attribute(text: str) -> tuple[str, float]:
    name, separator, value = text.partition("=")
    if not separator or not name.strip():
        raise argparse.ArgumentTypeError(
            f"attribut attendu sous la forme nom=valeur, reçu '{text}'"
        )
    try:
        return name.strip(), float(value.strip().replace(",", "."))
    except ValueError as exc:
        raise argparse.ArgumentTypeError(f"valeur numérique invalide dans '{text}'") from exc


def _attributes(pairs: Sequence[tuple[str, float]]) -> dict[str, float]:
    attributes: dict[str, float] = {}
    for name, value in pairs:
        if name in attributes:
            raise ValueError(f"attribut '{name}' fourni plusieurs fois.")
        attributes[name] = value
    return attributes


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="fuzzyscout",
        description="Aide au scouting de joueurs par logique floue.",
    )
    parser.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    parser.add_argument("--players", metavar="CSV", help="fichier CSV des joueurs")
    parser.add_argument(
        "--knowledge-dir", metavar="DIR", help="répertoire des bases de connaissances"
    )
    parser.add_argument("--log-level", default=None, help="DEBUG, INFO, WARNING, ERROR")
    subparsers = parser.add_subparsers(dest="command", required=True)

    positions = subparsers.add_parser("positions", help="lister les postes évaluables")
    positions.add_argument("--json", action="store_true", help="sortie JSON")

    rank = subparsers.add_parser("rank", help="classer les joueurs pour un poste")
    rank.add_argument("--position", required=True, help="code du poste (voir `positions`)")
    rank.add_argument("--top", type=int, default=None, help="ne garder que les N premiers")
    rank.add_argument("--max-age", type=float, help="âge maximal")
    rank.add_argument("--max-value", type=float, help="valeur marchande maximale (M€)")
    rank.add_argument("--min-minutes", type=float, help="temps de jeu minimal (minutes)")
    rank.add_argument("--nationality", help="code nationalité (ex. MA)")
    rank.add_argument("--natural-only", action="store_true", help="poste naturel uniquement")
    rank.add_argument("--explain", action="store_true", help="détailler les règles déclenchées")
    rank.add_argument("--json", action="store_true", help="sortie JSON")

    evaluate = subparsers.add_parser("evaluate", help="évaluer un joueur pour un poste")
    evaluate.add_argument("--position", required=True)
    group = evaluate.add_mutually_exclusive_group(required=True)
    group.add_argument("--player", help="identifiant du joueur dans le CSV")
    group.add_argument(
        "--attr",
        type=_parse_attribute,
        action="append",
        metavar="NOM=VALEUR",
        help="évaluation ad hoc : attributs d'un joueur absent du CSV (répétable)",
    )
    evaluate.add_argument("--name", default="Candidat ad hoc", help="nom du candidat ad hoc")
    evaluate.add_argument("--explain", action="store_true")
    evaluate.add_argument("--json", action="store_true")

    validate = subparsers.add_parser(
        "validate", help="charger et valider toutes les bases de connaissances"
    )
    validate.add_argument("--json", action="store_true", help="sortie JSON")

    serve = subparsers.add_parser("serve", help="démarrer l'API HTTP (nécessite l'extra [api])")
    serve.add_argument("--host", default="127.0.0.1")
    serve.add_argument("--port", type=int, default=8000)
    serve.add_argument("--reload", action="store_true")
    return parser


def _emit(data: Any, as_json: bool, text: str) -> None:
    print(json.dumps(data, ensure_ascii=False, indent=2) if as_json else text)


def _run(args: argparse.Namespace, service: ScoutingService) -> int:
    if args.command == "positions":
        positions = service.positions()
        _emit(
            [presenters.position_to_dict(p) for p in positions],
            args.json,
            presenters.format_positions(positions),
        )
        return 0
    if args.command == "rank":
        request = RankingRequest(
            position_code=args.position,
            filters=RankingFilters(
                max_age=args.max_age,
                max_market_value=args.max_value,
                min_minutes=args.min_minutes,
                natural_position_only=args.natural_only,
                nationality=args.nationality,
            ),
            limit=args.top,
        )
        report = service.rank(request)
        _emit(
            presenters.ranking_to_dict(report, include_trace=args.explain),
            args.json,
            presenters.format_ranking(report, explain=args.explain),
        )
        return 0
    if args.command == "evaluate":
        if args.player:
            evaluation = service.evaluate(args.position, args.player)
        else:
            evaluation = service.evaluate_attributes(
                args.position, _attributes(args.attr), args.name
            )
        _emit(
            presenters.evaluation_to_dict(evaluation, include_trace=args.explain),
            args.json,
            presenters.format_evaluation(evaluation, explain=args.explain),
        )
        return 0
    if args.command == "validate":
        summaries = service.validate_knowledge()
        _emit(
            presenters.knowledge_to_dict(summaries),
            args.json,
            presenters.format_knowledge(summaries),
        )
        return 0
    if args.command == "serve":
        return _serve(args)
    raise AssertionError(f"commande inconnue : {args.command}")  # pragma: no cover


def _serve(args: argparse.Namespace) -> int:
    try:
        import uvicorn
    except ImportError:  # pragma: no cover - depends on optional extra
        print(
            "L'API nécessite les dépendances optionnelles : pip install 'fuzzy-scouting[api]'",
            file=sys.stderr,
        )
        return 1
    uvicorn.run(
        "fuzzyscout.interfaces.api.app:create_app",
        factory=True,
        host=args.host,
        port=args.port,
        reload=args.reload,
    )
    return 0


def main(argv: Sequence[str] | None = None, service: ScoutingService | None = None) -> int:
    ensure_utf8_console()
    parser = build_parser()
    args = parser.parse_args(argv)
    settings = Settings.from_env().with_overrides(args.knowledge_dir, args.players)
    configure_logging(args.log_level or settings.log_level)
    try:
        return _run(args, service or build_service(settings))
    except (ScoutingError, FuzzyEngineError, ValueError, OSError) as exc:
        logger.debug("échec de la commande", exc_info=exc)
        print(f"Erreur : {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":  # pragma: no cover
    sys.exit(main())
