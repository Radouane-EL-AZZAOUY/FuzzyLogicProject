# 2. Fondements théoriques : du Prolog du cours au Prolog flou

Ce chapitre montre que `fuzzyprolog` **est** le système de la seconde moitié du cours
*Programmation logique* (logique des prédicats, unification, résolution, Prolog), auquel on ajoute
une seule idée : les valeurs de vérité vivent dans `[0, 1]` au lieu de `{Vrai, Faux}`. Chaque
section cite la page du support `logique des prédicats 2020.pdf` qu'elle implémente.

## 2.1 Ce que le moteur reprend tel quel

| Notion du cours | Page | Implémentation |
|---|---|---|
| Alphabet : constantes (minuscules, nombres), variables (majuscules), prédicats, fonctions | 41 | `terms.Atom`, `Number`, `String`, `Var`, `Struct` ; lexer `parser/lexer.py` |
| Terme, atome, fbf (définition récursive) | 42 | `terms.py`, grammaire de `parser/parser.py` |
| Substitution `σ = {(X\|t), …}` et application `A σ` | 54 | `substitution.Substitution` (`bind`, `resolve`) |
| Unificateur, unificateur le plus général, renommage | 55, 60 | `unification.unify`, `substitution.Renamer` |
| Algorithme d'unification (symbole le plus à gauche en désaccord, « variable incluse dans l'autre » ⇒ échec) | 56 | `unification.unify` avec *occurs check* |
| Résolution `H, G ⊢res K` avec renommage θ et unificateur σ | 60-61 | `engine.Engine._resolve` |
| Réfutation : déduire la clause vide de `H ∪ {¬C}` | 63 | une requête est la négation du but ; une solution est une réfutation |
| Stratégies : restreindre et ordonner les choix | 69 | ordre des clauses, profondeur d'abord, λ-coupure |
| Faits, questions, règles (clauses de Horn `Tête :- C1, …, Cn`) | 73-75 | `program.Clause`, `Program` |
| Listes, `[X\|L]`, `app/2`, `long/2`, `intersection/3` | 76-77 | `prelude.pl` (mêmes noms que le cours) |
| Arbre ET/OU, but courant, substitutions propagées, backtracking | 79-80 | générateurs Python de `Engine._solve` |
| Négation par l'échec `not/1` (monde clos) | 81 | `\+/1`, `not/1` |
| Coupe-choix `!` et son effet sur le nombre de solutions | 82-83 | barrières de coupure de `Engine` ; test reproduisant 6/1/3/5 |
| Récursivité (`factoriel`) | 84 | test `test_p84_recursion_factorial` |

Les tests `tests/engine/test_course_examples.py` rejouent les exemples des pages 75, 77, 78-80, 81,
83 et 84 et vérifient les réponses du support (par exemple `X = aicha` pour
`est_de_bonne_humeur(X)` et les nombres de solutions 6, 1, 3, 5 de la page 83).

## 2.2 Pourquoi graduer la logique des prédicats

Le cours interprète un prédicat d'arité *n* comme une application `Dⁿ → {Vrai, Faux}` (p. 46) et
l'unification échoue dès que deux constantes diffèrent (p. 56 : « si aucune n'est une variable
… alors A et B ne sont pas unifiables »). Pour le rapprochement d'identités, c'est précisément
le problème : `mohamed` et `mohammed` sont deux constantes distinctes qui désignent presque
sûrement la même personne. Les deux extensions suivantes rendent ce « presque » calculable.

## 2.3 Extension 1 : des axiomes gradués

Une clause porte un **degré de vérité** `d ∈ ]0, 1]` :

```prolog
aime(ali, foot) @ 0.8.                                  % fait vrai au degré 0.8
passionne(X) :- aime(X, foot) @ 0.9.                    % règle fiable au degré 0.9
```

Un degré absent vaut 1 : tout programme Prolog ordinaire est un programme flou. Cette idée est
celle des programmes logiques annotés / multi-adjoints (Medina, Ojeda-Aciego, Vojtáš, 2001) :
l'implication de la règle est pondérée par la confiance qu'on lui accorde.

## 2.4 Extension 2 : l'unification par similarité

Soit `R` une **relation de similarité** sur les constantes : réflexive (`R(a,a) = 1`), symétrique,
et transitive au sens max-min (`R(a,c) ≥ min(R(a,b), R(b,c))`). Elle est déclarée dans le
programme et fermée automatiquement :

```prolog
"Mohamed" ~ "Mohammed" @ 0.9.
"Mohammed" ~ "Muhammad" @ 0.8.        % ⇒ R("Mohamed", "Muhammad") = 0.8 par transitivité
casablanca ~ casa @ 0.95.
```

L'**unification faible** (Sessa, 2002 ; Bousi~Prolog) modifie **un seul cas** de l'algorithme de la
page 56 : quand les deux sous-termes en désaccord sont des constantes `a ≠ b`, au lieu d'échouer
on retourne `R(a, b)` ; l'unification réussit au degré `T` (t-norme) des similarités rencontrées,
et échoue si une similarité vaut 0. Tout le reste (variables, occurs check, structures de même
foncteur et arité) est inchangé (`unification.unify`).

Conséquence : `habite(B, casablanca)` s'unifie avec le fait `habite(p2, casa)` au degré 0.95,
sans qu'aucune règle n'ait à le prévoir.

## 2.5 Extension 3 : la résolution SLD graduée

Le cours décrit une résolution comme une suite d'inférences (p. 45 : « Preuve : ensemble
d'inférences conduisant aux théorèmes »). Dans la version graduée, chaque inférence apporte un
degré et la dérivation vaut leur **t-norme** :

```
deg(dérivation) = T( deg(clause₁), deg(σ₁), deg(clause₂), deg(σ₂), …, deg(prédéfini_k), … )
```

avec `T = min` par défaut (`product` ou `lukasiewicz` par directive `:- tnorm(...)`). Quand
plusieurs dérivations prouvent la même réponse, l'application retient la meilleure (borne
supérieure, comme dans les sémantiques MALP). Propriétés :

- **Extension conservative** : sans degré `@` et sans déclaration `~`, chaque étape vaut 1,
  `T(1, …, 1) = 1` et l'on retrouve exactement la résolution SLD du cours (tests des exemples
  du support).
- **λ-coupure** : une directive `:- lambda_cut(λ)` abandonne toute dérivation dont le degré
  tombe sous λ. C'est une *stratégie* au sens de la page 69 (restreindre les choix) : elle ne
  change pas les réponses de degré ≥ λ et rend la recherche tractable.
- **Négation par l'échec graduée** : `\+ G` vaut `1 − sup{deg(dérivations de G)}` ; elle vaut 1
  si `G` échoue et 0 si `G` est prouvé au degré 1 (p. 81 retrouvée sur `{0, 1}`).
- **Prédéfinis gradués** : un prédicat prédéfini peut réussir avec un degré (`text_similar/2`,
  `number_close/3`, et ceux de l'application : `nom_similaire/2`, `date_proche/2`…). C'est le
  point d'extension qui relie le raisonnement symbolique aux mesures numériques.

Le coupe-choix, `call/N`, `findall/3`, l'arithmétique (`is/2`) et l'ordre standard des termes
(`@</2`) gardent leur sémantique Prolog ; `findall/3` collecte les instances sans leur degré.

## 2.6 Un système formel, au sens du cours

| Système formel (p. 33) | `fuzzyprolog` |
|---|---|
| Alphabet | symboles du lexer : atomes, variables, nombres, chaînes, `:-`, `@`, `~`, `!`, `\+` |
| Langage | clauses `Tête :- Corps @ d.`, déclarations `a ~ b @ d.`, directives `:- …` |
| Axiomes | les clauses du programme (et les similarités) |
| Règles de déduction | résolution graduée (modus ponens généralisé) ; négation par l'échec |
| Dérivation `E₁ … Eₙ` | la trace `Solution.steps` (une `ProofStep` par inférence) |
| Théorème | une réponse `X = aicha (0.80)` |

La trace imprimée par `--explain` est littéralement la dérivation : chaque ligne nomme le but,
la clause utilisée (avec sa ligne source), le degré de l'étape et les similarités invoquées.

## 2.7 Ce que l'on ne reprend pas

- La résolution générale par réfutation sur clauses quelconques (p. 57-70) : comme Prolog, le
  moteur se limite aux clauses de Horn et à la stratégie linéaire en profondeur d'abord.
- La mise en forme clausale (p. 66) : les programmes sont écrits directement sous forme de
  clauses.
- L'unification faible sur les **foncteurs** (autorisée dans Bousi~Prolog) : seules les
  constantes sont similaires, choix qui garde les règles lisibles.

## 2.8 Lien avec la logique floue classique

Les t-normes `min`, `produit` et `Łukasiewicz` sont celles des ensembles flous (Zadeh, 1965) ; la
similarité `R` est une relation floue d'équivalence ; `1 − sup` est la négation standard. La
différence avec un contrôleur de Mamdani : ici la logique floue s'applique à la **déduction
symbolique** (termes, variables, unification), pas seulement à des valeurs numériques.

## 2.9 Références

- M. Ramdani, *Programmation logique*, support ILISI (pages citées ci-dessus).
- M. I. Sessa, « Approximate reasoning by similarity-based SLD resolution », *Theoretical
  Computer Science* 275, 2002.
- P. Julián-Iranzo, C. Rubio-Manzano, « Bousi~Prolog: a fuzzy logic programming language for
  modeling vague knowledge », *Fuzzy Sets and Systems* 2017.
- J. Medina, M. Ojeda-Aciego, P. Vojtáš, « Multi-adjoint logic programming with continuous
  semantics », *LPNMR* 2001.
- L. A. Zadeh, « Fuzzy sets », *Information and Control* 8, 1965.
