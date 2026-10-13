# Raccourcis de développement. Sous Windows sans `make`, exécuter les commandes
# équivalentes listées dans docs/07-guide-developpeur.md.

PYTHON ?= python
VENV   ?= .venv
BIN     = $(VENV)/Scripts
ifeq ($(OS),Windows_NT)
    PY = $(BIN)/python.exe
else
    BIN = $(VENV)/bin
    PY  = $(BIN)/python
endif

.PHONY: help venv install test cov lint typecheck format check data demo api docker clean

help:
	@echo "venv       - créer l'environnement virtuel"
	@echo "install    - installer le projet en mode éditable avec les extras api et dev"
	@echo "test       - lancer la suite de tests"
	@echo "cov        - tests + rapport de couverture"
	@echo "lint       - ruff (style) ; format - ruff format"
	@echo "typecheck  - mypy strict"
	@echo "check      - format-check + lint + typecheck + tests (porte qualité)"
	@echo "data       - régénérer le jeu de données synthétique"
	@echo "demo       - classement de démonstration (attaquants)"
	@echo "api        - démarrer l'API HTTP sur http://127.0.0.1:8000"
	@echo "docker     - construire et lancer l'API en conteneur"

venv:
	$(PYTHON) -m venv $(VENV)

install:
	$(PY) -m pip install --upgrade pip
	$(PY) -m pip install -e ".[api,dev]"

test:
	$(PY) -m pytest

cov:
	$(PY) -m pytest --cov=src --cov-report=term-missing --cov-report=html

lint:
	$(PY) -m ruff check src tests scripts

format:
	$(PY) -m ruff format src tests scripts

typecheck:
	$(PY) -m mypy

check:
	$(PY) -m ruff format --check src tests scripts
	$(PY) -m ruff check src tests scripts
	$(PY) -m mypy
	$(PY) -m pytest

data:
	$(PY) scripts/generate_sample_players.py

demo:
	$(PY) -m fuzzyscout.interfaces.cli rank --position attaquant --top 10 --explain

api:
	$(PY) -m fuzzyscout.interfaces.cli serve --host 127.0.0.1 --port 8000

docker:
	docker compose -f docker/docker-compose.yml up --build

clean:
	-rm -rf build dist .pytest_cache .mypy_cache .ruff_cache htmlcov .coverage
	-find . -name "__pycache__" -type d -exec rm -rf {} +
