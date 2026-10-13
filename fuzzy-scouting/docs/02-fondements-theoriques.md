# 2. Fondements théoriques : du cours de logique à la logique floue

Ce chapitre relie le projet au cours *Programmation logique* (M. Ramdani, ILISI) : logique des
propositions, systèmes formels, logique des prédicats du premier ordre et Prolog. La logique floue
n'y est pas traitée explicitement ; nous la présentons comme une **extension conservative** de ces
notions, en gardant le vocabulaire du cours à chaque étape. Les numéros de page renvoient au
support `logique des prédicats 2020.pdf`.

## 2.1 Rappel : ce que le cours fixe

| Notion du cours | Page | Définition retenue |
|---|---|---|
| Proposition | 8 | Énoncé « soit vrai soit faux mais pas les deux » |
| Valeurs de vérité | 14 | `{□, ■}` (0 / 1) |
| Formule bien formée (fbf) | 12 | Définition récursive : `F = p` \| `¬H` \| `H □ K`, `□ ∈ {∧, ∨, →, ↔}` |
| Priorité des connecteurs | 13 | `¬` > `∧` > `∨` > `→` > `↔` (règles d'élimination des parenthèses) |
| Interprétation | 16 | `δ : P → {□, ■}` |
| Tables de vérité | 15 | Opérateurs `∧`, `∨`, `→`, `↔` |
| Équivalences remarquables | 22-25 | De Morgan, distributivité, éléments neutres, **tiers exclu**, **non-contradiction** |
| Système formel | 33 | Alphabet, langage, axiomes, règles de déduction ; une dérivation est une suite `E1 … En` |
| Prédicat d'arité *n* | 46 | Application `Dⁿ → {Vrai, Faux}` |
| Règles d'inférence | 44-45 | Modus ponens `G → H, G ⊢ H`, spécialisation universelle, modus tollens |
| Clauses de Horn / Prolog | 75 | `Tête :- C1, C2, …, Cn` : la tête est vraie si chaque `Ci` est vrai |
| Chaînage arrière, backtracking | 79-80 | Stratégie d'exploration de Prolog |

## 2.2 Pourquoi la logique bivalente ne suffit pas au scouting

Un recruteur raisonne avec des prédicats **vagues** : « *rapide* », « *jeune* », « *bon dans les
airs* ». En logique classique, `Rapide(x)` exige un seuil : 34,0 km/h est rapide, 33,9 ne l'est pas.
Ce seuil est arbitraire et produit des effets de bord absurdes (paradoxe sorite) : deux joueurs
quasi identiques reçoivent des verdicts opposés. Le cours lui-même pose qu'une proposition est
vraie « si adéquation entre proposition et faits du monde réel » (p. 9) ; pour un prédicat vague,
l'adéquation est **partielle**.

La logique floue (Zadeh, 1965) garde toute la machinerie du cours (formules, interprétations,
règles d'inférence) et ne change qu'une chose : l'ensemble des valeurs de vérité devient
l'intervalle `[0, 1]`.

## 2.3 Ensembles flous et prédicats flous

**Ensemble flou.** Un sous-ensemble classique `A ⊆ D` est caractérisé par sa fonction indicatrice
`χ_A : D → {0, 1}`. Un ensemble flou est caractérisé par une **fonction d'appartenance**
`μ_A : D → [0, 1]` ; `μ_A(x)` est le *degré* avec lequel `x` appartient à `A`.

**Prédicat flou.** Le cours définit un prédicat d'arité 1 comme une application `D → {Vrai, Faux}`
(p. 46). Un prédicat flou est une application `D → [0, 1]`. Dans le projet, chaque terme
linguistique est un prédicat flou (`fuzzyengine.variables.FuzzySet`) :

```
μ_rapide(vitesse) =  0            si vitesse ≤ 34
                     (v - 34)/1.5 si 34 < v < 35.5
                     1            si v ≥ 35.5
```

**Variable linguistique.** Un triplet `(nom, univers D, termes)` regroupant les prédicats flous
que l'on peut énoncer sur une grandeur : `vitesse ∈ {lente, moyenne, rapide}`
(`fuzzyengine.variables.LinguisticVariable`). Les formes d'appartenance implémentées
(`fuzzyengine.membership`) sont : triangle, trapèze, rampes (épaules), gaussienne, singleton.

**Fuzzification = interprétation.** Le cours associe à chaque variable propositionnelle une
interprétation `δ : P → {□, ■}` (p. 16). Ici, mesurer `vitesse = 34.6` et calculer
`μ_lente(34.6) = 0, μ_moyenne(34.6) = 0.2, μ_rapide(34.6) = 0.4` revient à construire
l'interprétation `δ(vitesse EST rapide) = 0.4` (`fuzzyengine.fuzzification.Fuzzifier` →
`fuzzyengine.formulas.Interpretation`).

## 2.4 Connecteurs : des tables de vérité aux normes triangulaires

Le cours associe à chaque connecteur un opérateur sur `{□, ■}` (p. 14-15). En logique floue on
associe à `∧` une **t-norme** `T`, à `∨` une **t-conorme** `S` et à `¬` un **complément** `N`,
fonctions de `[0,1]²` (resp. `[0,1]`) dans `[0,1]`. Familles implémentées
(`fuzzyengine.operators`) :

| Famille | `a ∧ b` | `a ∨ b` | `¬a` |
|---|---|---|---|
| Zadeh (défaut) | `min(a, b)` | `max(a, b)` | `1 − a` |
| Probabiliste | `a · b` | `a + b − a·b` | `1 − a` |
| Łukasiewicz | `max(0, a + b − 1)` | `min(1, a + b)` | `1 − a` |

**Extension conservative.** Restreintes à `{0, 1}`, les trois familles redonnent exactement les
tables de vérité du cours (test `test_operators.py::test_restricted_to_binary_values…`). Les
propriétés suivantes du cours (p. 22-25) restent vraies pour tout degré : commutativité,
associativité, éléments neutres (`F ∧ ■ ↔ F`, `F ∨ □ ↔ F`), éléments absorbants, double négation,
lois de De Morgan (famille de Zadeh).

**Ce qui est perdu.** Le **tiers exclu** `⊢ F ∨ ¬F` et la **non-contradiction** `⊢ ¬(F ∧ ¬F)`
(p. 24) ne tiennent plus : avec `δ(F) = 0.5`, `max(0.5, 1 − 0.5) = 0.5 ≠ 1`. C'est la propriété
caractéristique de la logique floue : une proposition peut être « à moitié vraie ». Le test
`test_excluded_middle_is_lost_in_fuzzy_logic` le vérifie, et montre que la famille de Łukasiewicz
conserve le tiers exclu (somme bornée).

## 2.5 Formules bien formées floues

La définition récursive des fbf du cours (p. 12) est reprise **telle quelle** dans
`fuzzyengine.formulas` :

```
Formule := Atome                          -- variable EST [modificateur] terme
         | Not(Formule)                   -- ¬
         | And(Formule, Formule)          -- ∧
         | Or(Formule, Formule)           -- ∨
```

La valeur de vérité d'une formule sous une interprétation `δ` se calcule par récurrence
structurelle, comme dans le cours, en remplaçant les tables par `T`, `S`, `N` :

```
v(p)       = δ(p)
v(¬H)      = N(v(H))
v(H ∧ K)   = T(v(H), v(K))
v(H ∨ K)   = S(v(H), v(K))
```

La priorité `¬ > ∧ > ∨` (p. 13) est utilisée par l'analyseur syntaxique du langage de règles et
par le rendu textuel sans parenthèses superflues (`test_formulas.py::test_rendering_follows_course_parenthesis_rules`
reprend les exemples de la p. 13).

**Modificateurs linguistiques.** `très` (concentration `μ²`), `assez` (dilatation `√μ`),
`extrêmement` (`μ³`) permettent d'écrire `vitesse EST très rapide` sans créer un nouveau terme.

## 2.6 Règles floues et modus ponens généralisé

Une règle `SI A ALORS c EST t` est la version graduée d'une **clause de Horn** du cours (p. 75)
`t(c) :- A1, A2, …, An` : la tête est vraie *au degré* auquel le corps est vrai.

Le **modus ponens** du cours (p. 44) :

```
G → H
G
-----
H
```

devient le **modus ponens généralisé** : de `G → H` et d'une prémisse `G'` vraie au degré
`α = v(G')`, on conclut `H'`, un ensemble flou obtenu par *implication* de `H` à la force `α`.
Dans la méthode de Mamdani (1975) implémentée (`fuzzyengine.inference.MamdaniInference`) :

1. **Activation** : `α_r = poids_r × v(antécédent_r)` pour chaque règle `r`.
2. **Implication** : `μ_{H'_r}(y) = I(α_r, μ_{t_r}(y))` avec `I = min` (écrêtage, Mamdani) ou
   `I = ×` (Larsen).
3. **Agrégation** : toutes les règles concluant sur la même variable sont combinées par une
   t-conorme (`max` par défaut) : `μ_out(y) = S_r μ_{H'_r}(y)`.
4. **Défuzzification** : on résume l'ensemble flou de sortie par un nombre, par défaut le centre
   de gravité `y* = Σ y μ_out(y) / Σ μ_out(y)` (ou bissectrice, moyenne des maxima).

## 2.7 Le système flou comme système formel

Le cours définit un système formel par un alphabet, un langage, des axiomes et des règles de
déduction (p. 33). `fuzzyengine.system.FuzzySystem` en est une instance :

| Système formel (cours, p. 33) | `FuzzySystem` |
|---|---|
| Alphabet | Noms de variables, de termes, mots-clés `SI/ALORS/ET/OU/NON/EST` |
| Langage (fbf) | Formules produites par la grammaire de `fuzzyengine.dsl` |
| Axiomes | La base de règles **et**, à l'exécution, les faits fuzzifiés |
| Règles de déduction | Modus ponens généralisé |
| Dérivation `E1, …, En` | Un appel à `evaluate()` ; dans un pipeline, chaque étape utilise les théorèmes des précédentes |
| Théorème | La conclusion défuzzifiée (ex. `aptitude = 78.4`, « bonne ») |

## 2.8 Chaînage avant plutôt que résolution

Prolog (cours p. 79-80) prouve un but par **chaînage arrière** avec unification et backtracking.
Le scouting pose un problème différent : on connaît *tous* les faits (les statistiques mesurées) et
on veut *toutes* les conclusions. Le moteur utilise donc le **chaînage avant** : toutes les règles
sont activées en parallèle, sans recherche ni retour arrière, et le résultat est déterministe.

Il n'y a pas non plus d'unification : chaque atome `vitesse EST rapide` est un prédicat d'arité 1
appliqué à une constante (la mesure). La **spécialisation universelle** du cours (p. 44) est
réalisée implicitement : la règle `∀X Rapide(X) ∧ Jeune(X) → Excellent(X)` est instanciée pour le
joueur évalué. Ces limites sont assumées (voir `ADR-002`).

## 2.9 Correspondance cours ↔ code

| Cours | Module / classe |
|---|---|
| Variables propositionnelles `P` | `formulas.Atom` (couple variable, terme) |
| Connecteurs `¬ ∧ ∨` | `formulas.Not / And / Or`, `operators.FuzzyOperators` |
| Interprétation `δ` | `formulas.Interpretation`, construite par `fuzzification.Fuzzifier` |
| Tables de vérité | `operators` (t-normes, t-conormes, complément) |
| Prédicat `D → {V, F}` | `variables.FuzzySet` (`D → [0,1]`) |
| Fbf (définition récursive) | `formulas.Formula` et sous-classes |
| Priorité des connecteurs | `dsl/parser.py` (grammaire), `Formula.precedence` |
| Clause de Horn | `rules.Rule` |
| Axiomes | `rules.RuleBase` |
| Modus ponens | `inference.MamdaniInference` |
| Système formel | `system.FuzzySystem` |
| Suite de dérivations | `pipeline.FuzzyPipeline` |
| Preuve (trace) | `inference.RuleActivation`, `explanation.explain_result` |

## 2.10 Références

- L. A. Zadeh, *Fuzzy sets*, Information and Control 8(3), 1965.
- E. H. Mamdani, S. Assilian, *An experiment in linguistic synthesis with a fuzzy logic controller*,
  Int. J. Man-Machine Studies 7, 1975.
- H.-J. Zimmermann, *Fuzzy Set Theory and Its Applications*, Kluwer, 2001.
- M. Ramdani, *Programmation logique*, support de cours ILISI (fichier `logique des prédicats 2020.pdf`).
