#!/usr/bin/env bash
# Lanceur du projet pour Linux / macOS (équivalent de scout.cmd).
#
#   ./scout.sh                 démarre l'interface web (installe le projet si besoin) et ouvre le navigateur
#   PORT=8080 ./scout.sh web   idem sur un autre port ; NO_BROWSER=1 pour ne pas ouvrir le navigateur
#   ./scout.sh setup           crée l'environnement virtuel et installe le projet
#   ./scout.sh test            lance les tests
#   ./scout.sh check           porte qualité : format, lint, typage strict, tests
#   ./scout.sh demo            classement de démonstration dans le terminal
set -euo pipefail

cd "$(dirname "$0")"
PY=".venv/bin/python"
PORT="${PORT:-8000}"
ADDRESS="${ADDRESS:-127.0.0.1}"
URL="http://$ADDRESS:$PORT"

say() { printf '\033[32m[fuzzy-scouting] %s\033[0m\n' "$*"; }
fail() { printf '\033[31m[fuzzy-scouting] %s\033[0m\n' "$*" >&2; exit 1; }

# Vrai si le projet est importable depuis ce dossier, avec ses dépendances web et de test.
installed() {
  [ -x "$PY" ] && "$PY" -c "
import sys, pathlib, fuzzyscout, fastapi, uvicorn, pytest
here = pathlib.Path.cwd().resolve()
sys.exit(0 if pathlib.Path(fuzzyscout.__file__).resolve().is_relative_to(here) else 1)" 2>/dev/null
}

install() {
  if [ ! -x "$PY" ]; then
    say "Création de l'environnement virtuel (.venv)…"
    python3 -m venv .venv || fail "Impossible de créer .venv : Python 3.11 ou plus récent est requis."
  fi
  say "Installation du projet et de ses dépendances…"
  "$PY" -m pip install --quiet --disable-pip-version-check -e ".[api,dev]"
  say "Installation terminée."
}

ensure() { installed || install; }

healthy() { "$PY" -c "
import sys, urllib.request
try:
    sys.exit(0 if urllib.request.urlopen('$URL/health', timeout=2).status == 200 else 1)
except Exception:
    sys.exit(1)"; }

open_browser() {
  [ -n "${NO_BROWSER:-}" ] && return 0
  if command -v xdg-open >/dev/null; then xdg-open "$URL" >/dev/null 2>&1 || true
  elif command -v open >/dev/null; then open "$URL" || true
  fi
}

web() {
  if healthy; then
    say "Le serveur tourne déjà sur $URL."
    open_browser
    return
  fi
  # Ouvre le navigateur dès que le serveur répond (au plus 30 s d'attente).
  ( for _ in $(seq 60); do healthy && { open_browser; break; }; sleep 0.5; done ) &
  say "Interface web : $URL   (Ctrl+C pour arrêter)"
  exec "$PY" -m fuzzyscout.interfaces.cli serve --host "$ADDRESS" --port "$PORT"
}

case "${1:-web}" in
  help) grep '^#   ' "$0" | cut -c3- ;;
  setup) install ;;
  web) ensure; web ;;
  test) ensure; "$PY" -m pytest ;;
  check)
    ensure
    "$PY" -m ruff format --check src tests scripts
    "$PY" -m ruff check src tests scripts
    "$PY" -m mypy
    "$PY" -m pytest
    say "Porte qualité verte."
    ;;
  demo) ensure; "$PY" -m fuzzyscout.interfaces.cli rank --position attaquant --top 10 --min-minutes 900 ;;
  *) fail "Commande inconnue : $1 (voir ./scout.sh help)" ;;
esac
