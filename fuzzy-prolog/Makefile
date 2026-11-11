PYTHON ?= python
VENV   ?= .venv
ifeq ($(OS),Windows_NT)
    PY = $(VENV)/Scripts/python.exe
else
    PY = $(VENV)/bin/python
endif

.PHONY: help venv install test cov lint format typecheck check data demo repl

help:
	@echo "venv install test cov lint format typecheck check data demo repl"

venv:
	$(PYTHON) -m venv $(VENV)

install:
	$(PY) -m pip install --upgrade pip
	$(PY) -m pip install -e ".[dev]"

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
	$(PY) scripts/generate_sample_dataset.py

demo:
	$(PY) -m fuzzyprolog.cli examples/humeur.pl -q "est_de_bonne_humeur(X)." --explain
	$(PY) -m identitylink.interfaces.cli dedupe --threshold 0.7
	$(PY) -m identitylink.interfaces.cli evaluate

repl:
	$(PY) -m fuzzyprolog.cli examples/flou.pl
