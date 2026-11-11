"""Command-line interface ``fuzzyprolog``: run queries against program files, or a REPL.

fuzzyprolog famille.pl -q "grand_parent(X, Y)."
fuzzyprolog famille.pl                       # boucle interactive : ?- but.
"""

from __future__ import annotations

import argparse
import contextlib
import sys
from collections.abc import Sequence

from fuzzyprolog import __version__
from fuzzyprolog.engine import Engine
from fuzzyprolog.exceptions import FuzzyPrologError
from fuzzyprolog.loader import load_program
from fuzzyprolog.program import Settings
from fuzzyprolog.tnorms import tnorm_from_name


def ensure_utf8_console() -> None:
    for stream in (sys.stdout, sys.stderr):
        reconfigure = getattr(stream, "reconfigure", None)
        if reconfigure is not None:
            with contextlib.suppress(ValueError, OSError):
                reconfigure(encoding="utf-8", errors="replace")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="fuzzyprolog",
        description="Prolog flou : unification par similarité et résolution SLD graduée.",
    )
    parser.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    parser.add_argument("files", nargs="*", help="programmes à charger (.pl)")
    parser.add_argument(
        "-q", "--query", action="append", default=[], help="requête à exécuter (répétable)"
    )
    parser.add_argument("--max", type=int, default=20, help="nombre maximal de solutions affichées")
    parser.add_argument(
        "--lambda-cut", type=float, default=None, help="seuil λ de coupure des dérivations"
    )
    parser.add_argument("--tnorm", default=None, help="min | product | lukasiewicz")
    parser.add_argument(
        "--max-depth", type=int, default=None, help="profondeur de résolution maximale"
    )
    parser.add_argument(
        "--explain", action="store_true", help="afficher la preuve de chaque solution"
    )
    parser.add_argument(
        "--no-prelude", action="store_true", help="ne pas charger les prédicats de listes du cours"
    )
    return parser


def _settings(base: Settings, args: argparse.Namespace) -> Settings:
    settings = base
    if args.lambda_cut is not None:
        settings = settings.with_(lambda_cut=args.lambda_cut)
    if args.tnorm is not None:
        settings = settings.with_(tnorm=tnorm_from_name(args.tnorm))
    if args.max_depth is not None:
        settings = settings.with_(max_depth=args.max_depth)
    return settings


def run_query(engine: Engine, text: str, limit: int, explain: bool) -> int:
    """Print the solutions of ``text``; return their number."""
    count = 0
    for solution in engine.query(text, limit=limit):
        count += 1
        print(solution.explain() if explain else str(solution))
    if count == 0:
        print("non.")
    elif count >= limit:
        print(f"... (limite de {limit} solutions atteinte)")
    return count


def repl(engine: Engine, limit: int, explain: bool) -> int:
    print(f"fuzzyprolog {__version__} — tapez une requête terminée par '.', 'halt.' pour quitter.")
    while True:
        try:
            line = input("?- ").strip()
        except (EOFError, KeyboardInterrupt):
            print()
            return 0
        if not line:
            continue
        if line in {"halt.", "halt", "quit", "exit"}:
            return 0
        try:
            run_query(engine, line, limit, explain)
        except FuzzyPrologError as exc:
            print(f"Erreur : {exc}", file=sys.stderr)


def main(argv: Sequence[str] | None = None) -> int:
    ensure_utf8_console()
    args = build_parser().parse_args(argv)
    try:
        program = load_program(args.files, prelude=not args.no_prelude)
        engine = Engine(program, settings=_settings(program.settings, args))
        if not args.query:
            return repl(engine, args.max, args.explain)
        for text in args.query:
            print(f"?- {text}")
            run_query(engine, text, args.max, args.explain)
        return 0
    except FuzzyPrologError as exc:
        print(f"Erreur : {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":  # pragma: no cover
    sys.exit(main())
