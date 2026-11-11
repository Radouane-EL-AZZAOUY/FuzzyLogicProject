# Logique floue — deux projets d'IA symbolique

[![Python 3.11+](https://img.shields.io/badge/python-3.11%2B-blue.svg)](https://www.python.org/)
[![License: MIT](https://img.shields.io/badge/license-MIT-lightgrey.svg)](fuzzy-scouting/LICENSE)

Projets réalisés dans le cadre du module **IA classique / Programmation logique** (ILISI 3, FSTM).
Ils prolongent le cours — logique des propositions, logique des prédicats, unification,
résolution, Prolog — vers la **logique floue**, selon deux angles complémentaires :

| | [**fuzzy-scouting**](fuzzy-scouting/) | [**fuzzy-prolog**](fuzzy-prolog/) |
|---|---|---|
| **Idée** | Système expert flou (Mamdani) : règles `SI … ALORS …` sur des prédicats gradués | Prolog flou : unification par similarité et résolution SLD graduée |
| **Notions du cours généralisées** | Interprétation, fbf, modus ponens, clauses de Horn | Termes, unification, résolution, backtracking, coupe, négation par l'échec |
| **Moteur** | `fuzzyengine` — inférence floue générique, règles en TOML / langage quasi naturel | `fuzzyprolog` — interpréteur Prolog flou en Python pur, REPL et preuves |
| **Application** | `fuzzyscout` — classement de joueurs de football par poste, avec explication de chaque verdict (interface web + CLI + API HTTP) | `identitylink` — détection de doublons de personnes (*Mohamed / Mohammed / Muhammad*, villes alias, dates approximatives) |
| **2ᵉ démonstration** | `fuzzyirrigation` — contrôleur d'irrigation | Exemples du cours rejoués (famille, humeur, coupe-choix, listes) |
| **Tests** | 165 tests, couverture 96 % | 90 tests, couverture 93 % |

Les deux projets sont **indépendants** : chacun a son propre `pyproject.toml`, son environnement
virtuel, sa documentation, ses tests et son Dockerfile. Leurs cœurs n'ont aucune dépendance
externe.

## Démarrage rapide

Prérequis : Python ≥ 3.11. Chaque projet s'installe depuis son propre dossier.

```bash
# --- Système expert flou : scouting de joueurs ---
cd fuzzy-scouting
python -m venv .venv
.venv\Scripts\activate                 # Linux/macOS : source .venv/bin/activate
pip install -e ".[api,dev]"

fuzzyscout rank --position attaquant --top 5 --min-minutes 900
fuzzyscout evaluate --position attaquant --player P036 --explain
fuzzyscout serve                       # interface web sur http://127.0.0.1:8000 (API : /docs)
fuzzyirrigation decide --humidite-sol 18 --temperature 34 --humidite-air 28 --explain
```

```bash
# --- Prolog flou : rapprochement d'identités ---
cd fuzzy-prolog
python -m venv .venv
.venv\Scripts\activate                 # Linux/macOS : source .venv/bin/activate
pip install -e ".[dev]"

fuzzyprolog examples/famille.pl -q "grand_parent(X, Y)."
fuzzyprolog examples/flou.pl           # REPL flou (?- …)
identitylink dedupe --threshold 0.7 --explain
identitylink evaluate --errors         # précision / rappel / F1
```

Pour le scouting, le lanceur `scout` (`scout.cmd` sous Windows, `./scout.sh` ailleurs) fait tout en
une commande : installation, démarrage du serveur et ouverture de l'interface web.

Chaque projet fournit aussi un `Makefile` (`make install`, `make test`, `make check`,
`make demo`, …).

## Structure du dépôt

```
FuzzyLogicProject/
├── fuzzy-scouting/     système expert flou (fuzzyengine, fuzzyscout, fuzzyirrigation)
│   ├── src/  tests/  docs/  scripts/  docker/
│   └── README.md       présentation détaillée, exemples de sortie, documentation
└── fuzzy-prolog/       Prolog flou (fuzzyprolog, identitylink)
    ├── src/  tests/  docs/  examples/  scripts/  docker/
    └── README.md       présentation détaillée, exemple de preuve, documentation
```

## Documentation

Chaque projet contient un dossier `docs/` complet : problème et objectifs, fondements théoriques
(avec correspondance cours ↔ code), architecture, référence du moteur, guide de l'application,
guide du développeur, qualité et tests, décisions d'architecture (ADR) et glossaire.

- [fuzzy-scouting/README.md](fuzzy-scouting/README.md) · [fuzzy-scouting/docs/](fuzzy-scouting/docs/)
- [fuzzy-prolog/README.md](fuzzy-prolog/README.md) · [fuzzy-prolog/docs/](fuzzy-prolog/docs/)

## Auteur et licence

Radouane El Azzaouy — ILISI 3, FSTM, 2026.

Licence MIT (voir [fuzzy-scouting/LICENSE](fuzzy-scouting/LICENSE) et
[fuzzy-prolog/LICENSE](fuzzy-prolog/LICENSE)). Toutes les données embarquées (joueurs, clubs,
personnes) sont **synthétiques** et fictives.
