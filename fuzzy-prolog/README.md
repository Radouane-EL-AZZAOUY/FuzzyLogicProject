# Fuzzy Prolog — programmation logique floue et rapprochement d'identités

[![Python 3.11+](https://img.shields.io/badge/python-3.11%2B-blue.svg)](https://www.python.org/)
[![Tests](https://img.shields.io/badge/tests-90%20passed-brightgreen.svg)](docs/07-qualite-et-tests.md)
[![Coverage](https://img.shields.io/badge/coverage-93%25-brightgreen.svg)](docs/07-qualite-et-tests.md)
[![Typed](https://img.shields.io/badge/mypy-strict-blue.svg)](pyproject.toml)
[![License: MIT](https://img.shields.io/badge/license-MIT-lightgrey.svg)](LICENSE)

Projet d'**IA symbolique** (ILISI 3, FSTM) prolongeant le cours *Programmation logique*
(unification, résolution, Prolog) vers la **logique floue** : un moteur de **Prolog flou** écrit
en Python pur — unification par similarité, résolution SLD graduée, règles pondérées, coupe-choix,
négation par l'échec, preuves — et une application qui résout un problème réel : le
**rapprochement d'identités** (détection de doublons de personnes malgré les variantes de
translittération *Mohamed / Mohammed / Muhammad*, les dates approximatives et les villes alias).

```prolog
"Mohamed" ~ "Mohammed" @ 0.9.           % relation de similarité entre constantes
"Mohammed" ~ "Muhammad" @ 0.8.          % ⇒ "Mohamed" ~ "Muhammad" @ 0.8 (fermeture max-min)
casablanca ~ casa @ 0.95.

prenom(p1, "Mohamed").   habite(p1, casablanca).
prenom(p2, "Muhammad").  habite(p2, casa).

meme_prenom(A, B) :- prenom(A, P), prenom(B, P).      % l'unification réussit au degré 0.8
meme_ville(A, B)  :- habite(A, V), habite(B, V).      % ... et ici au degré 0.95
doublon(A, B) :- meme_prenom(A, B), meme_ville(A, B), A @< B @ 0.9.   % règle fiable à 0.9
```

```
?- doublon(A, B).
A = p1, B = p2 (0.80)
doublon(A, B)  <-  clause l.11 : doublon(A, B) :- meme_prenom(A, B), meme_ville(A, B), A @< B @ 0.9.  [0.90]
  meme_prenom(p1, p2)  <-  clause l.10 : meme_prenom(A, B) :- prenom(A, P), prenom(B, P).
    prenom(p1, "Mohamed")  <-  clause l.5 : prenom(p1, "Mohamed").
    prenom(p2, "Mohamed")  <-  clause l.6 : prenom(p2, "Muhammad").  [0.80]
        similarité "Mohamed" ~ "Muhammad" (0.80)
  meme_ville(p1, p2)  <-  clause l.9 : meme_ville(A, B) :- habite(A, V), habite(B, V).
    habite(p1, casablanca)  <-  clause l.7 : habite(p1, casablanca).
    habite(p2, casablanca)  <-  clause l.8 : habite(p2, casa).  [0.95]
        similarité casablanca ~ casa (0.95)
  p1 @< p2  <-  prédéfini @</2
```

## En quoi c'est différent

La plupart des projets « logique floue » sont des contrôleurs de Mamdani (irrigation, machine à
laver, notation). Ici la logique floue s'applique à la **déduction symbolique du cours** : termes,
variables, unification (p. 56), résolution (p. 60), backtracking (p. 80), coupe (p. 83) — chaque
notion est implémentée telle quelle, puis graduée. Sans degré ni similarité, le moteur **est** le
Prolog du cours : les exemples du support (famille, humeur, coupe-choix 6/1/3/5, listes,
factorielle) sont rejoués par les tests avec les réponses attendues.

## Démarrage rapide

```bash
python -m venv .venv && .venv\Scripts\activate        # Linux/macOS : source .venv/bin/activate
pip install -e ".[dev]"

# Le Prolog du cours
fuzzyprolog examples/famille.pl -q "grand_parent(X, Y)."
fuzzyprolog examples/humeur.pl  -q "est_de_bonne_humeur(X)." --explain      # arbre p. 80
fuzzyprolog examples/coupe.pl   -q "p2(X, Y)." -q "p3(X, Y)."              # coupe p. 83
fuzzyprolog examples/flou.pl                                                # REPL flou (?- …)

# L'application : doublons d'identité sur le jeu synthétique embarqué (257 fiches)
identitylink dedupe --threshold 0.7 --explain
identitylink evaluate --errors                 # précision / rappel / F1 contre la vérité terrain
identitylink query "meme_personne(p0118, X)." --explain
identitylink generate --out ./donnees --persons 300 --seed 42
```

Résultats sur le jeu embarqué (seuil 0,7) : voir [docs/05](docs/05-application-identitylink.md)
— précision 1,00, rappel 0,97, F1 0,98, aucun homonyme rapproché, ≈ 5 s pour 257 fiches.

## Structure

```
fuzzy-prolog/
├── src/fuzzyprolog/           moteur de Prolog flou (Python pur)
│   ├── terms.py substitution.py unification.py similarity.py tnorms.py
│   ├── program.py engine.py builtins.py solution.py loader.py cli.py
│   ├── parser/ (lexer, parseur à précédence)   operators.py   prelude.pl (listes du cours)
├── src/identitylink/          application de rapprochement d'identités
│   ├── domain/ (fiches, normalisation, résultats, ports)   application/ (dédoublonnage, évaluation)
│   ├── infrastructure/ (CSV, connaissances, données synthétiques)   interfaces/ (CLI, présentation)
│   ├── builtins.py (prédicats gradués)   knowledge/ (regles.pl, similarites.pl)   data/
├── examples/                  programmes du cours exécutables + flou.pl
├── tests/                     90 tests (moteur : exemples du cours ; application) — couverture 93 %
├── docs/                      documentation détaillée + ADR + glossaire
└── pyproject.toml Makefile docker/ .github/
```

## Documentation

| Chapitre | Contenu |
|---|---|
| [01 — Problème et objectifs](docs/01-probleme-et-objectifs.md) | Doublons d'identité, pourquoi le Prolog flou, périmètre |
| [02 — Fondements théoriques](docs/02-fondements-theoriques.md) | Du Prolog du cours (pages citées) à l'unification faible et à la résolution graduée |
| [03 — Architecture](docs/03-architecture.md) | Modules du moteur, couches de l'application, diagrammes, SOLID, scalabilité |
| [04 — Moteur et langage](docs/04-moteur-fuzzyprolog.md) | Syntaxe, directives, prédéfinis, sémantique des degrés, API, CLI |
| [05 — Application identitylink](docs/05-application-identitylink.md) | Données, normalisation, règles, rapports, évaluation, calibrage |
| [06 — Guide du développeur](docs/06-guide-developpeur.md) | Installation, commandes, conventions, points d'extension |
| [07 — Qualité et tests](docs/07-qualite-et-tests.md) | Stratégie, inventaire, propriétés garanties |
| [ADR](docs/adr/) | Moteur maison, générateurs, unification faible, blocage, frontière règles/prédéfinis |
| [Glossaire](docs/glossaire.md) | Vocabulaire |

## Licence

MIT. Les données de `src/identitylink/data/` sont synthétiques (personnes et noms fictifs).
