# 7. Qualité et tests

## 7.1 Stratégie

1. **Tests du cours** : chaque exemple du support (pages 54-56, 73-84) est un test dont la
   réponse attendue est celle du support.
2. **Tests des extensions floues** : degrés, similarités (transitivité), λ-coupure, négation
   graduée, prédéfinis gradués, explications.
3. **Tests du langage** : lexer, précédences, listes, erreurs localisées.
4. **Tests applicatifs** : normalisation (translittération, dates, téléphones), dédoublonnage
   d'un petit jeu contrôlé (y compris un homonyme qui ne doit pas être rapproché), métriques sur
   le jeu synthétique (précision ≥ 0,95, rappel ≥ 0,80), CSV, CLI.

## 7.2 Inventaire

| Fichier | Vérifie |
|---|---|
| `engine/test_parser.py` | tokens, `=..`, commentaires, apostrophes, listes, précédences (`1+2*3`, `a :- b, c ; d`), variables anonymes, degrés `@`, similarités `~`, erreurs avec position, rendu |
| `engine/test_unification_and_similarity.py` | **exemple p. 55** (`P(X,Z)` / `P(f(Y),g(a))`), **exemple p. 54** (application de σ), occurs check, échecs classiques, unification par similarité (min / produit, seuil), fermeture max-min, erreurs |
| `engine/test_course_examples.py` | **p. 73, 75, 77, 78-80, 81, 83, 84** : famille, listes, arbre de recherche (aicha via R2), négation, coupe (6/1/3/5), factorielle, ordre des solutions |
| `engine/test_fuzzy_resolution.py` | degrés de faits/règles et t-normes, similarité transitive en tête de clause, λ-coupure, négation `1 − sup`, prédéfinis flous, explication (niveaux, similarités), contrôle (`;`, `->`, `call`, coupe locale, `findall`), arithmétique, types, erreurs, API programme et indexation |
| `engine/test_cli.py` | requêtes en ligne de commande, `--explain`, limites, erreurs (code 1), REPL |
| `linkage/test_normalization.py` | variantes de translittération, clés, planchers, dates, téléphones, clés de blocage, invariants |
| `linkage/test_deduplicate.py` | faits générés, programme, petit jeu contrôlé (3 fiches d'une personne, homonyme exclu, alias de ville), union-find, **métriques sur le jeu embarqué**, paires de vérité |
| `linkage/test_csv_and_cli.py` | BOM, `;`, cp1252, formats de date, erreurs CSV, vérité terrain, reproductibilité du générateur, commandes `dedupe` / `evaluate` / `query` / `generate`, erreurs |
| `engine/test_review_fixes.py` | Régressions de la revue : apostrophes dans les atomes, variables anonymes, **négation saine sous λ-coupure**, copie du patron de `findall`, similarité numérique refusée, buts non appelables, dépassement arithmétique, index sur le 2ᵉ argument, message de profondeur |
| `linkage/test_review_fixes.py` | Options CLI par-dessus les directives, identifiants avec apostrophe, similarités géographiques exclues, squelette (*Nana/Na*, *Lotfi*), CSV illisible |

Total : 90 tests, ≈ 15 s (≈ 40 s avec mesure de couverture) ; couverture 93 % de `src/`
(lignes et branches).

## 7.3 Analyse statique

`ruff check` (E, F, W, I, N, UP, B, SIM, C4, RUF) : 0 avertissement ; `ruff format` conforme ;
`mypy --strict` : 0 erreur sur 37 fichiers.

## 7.4 Propriétés garanties par les tests

- Sans degré ni similarité, le moteur donne exactement les réponses et l'ordre du Prolog du cours.
- Les degrés sont dans `]0, 1]`, décroissants le long d'une dérivation (t-norme), et la λ-coupure
  ne supprime que des dérivations sous le seuil.
- La relation de similarité est réflexive, symétrique, transitive (max-min) et symétrique dans
  l'unification.
- Le coupe-choix est local à `call/1` et à la clause qui le contient ; la négation est opaque.
- Sur le jeu synthétique : aucun homonyme rapproché (précision 1,0), rappel ≥ 0,95 au seuil 0,7.

## 7.5 Liste de contrôle de revue

- [ ] Tout nouveau prédéfini a un test de degré et un test d'erreur d'instanciation.
- [ ] Toute modification de `regles.pl` est suivie d'un `identitylink evaluate` dont les métriques
      sont reportées dans le journal des modifications.
- [ ] Aucun import de `infrastructure`/`interfaces` dans `domain`/`application`.
- [ ] `make check` vert.
