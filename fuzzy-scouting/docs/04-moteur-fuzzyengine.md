# 4. Référence du moteur `fuzzyengine`

Bibliothèque d'inférence floue en Python pur (aucune dépendance), typée strictement (`mypy
--strict`). Tout est importable depuis `fuzzyengine` (`from fuzzyengine import *` expose l'API
publique listée dans `__all__`).

## 4.1 Modules

| Module | Contenu |
|---|---|
| `universe` | `Universe(lower, upper)` : intervalle, `clamp`, `grid(resolution)` |
| `membership` | `MembershipFunction` et formes concrètes ; `MEMBERSHIP_REGISTRY`, `membership_from_spec` |
| `variables` | `FuzzySet(label, membership)`, `LinguisticVariable(name, universe, terms, description, unit)` |
| `operators` | t-normes, t-conormes, compléments, implications ; familles `ZADEH`, `PROBABILISTIC`, `LUKASIEWICZ` |
| `modifiers` | Modificateurs linguistiques `very`, `somewhat`, `extremely` et alias français |
| `formulas` | AST `Atom`, `Not`, `And`, `Or` ; `Interpretation` ; `conjunction()` |
| `rules` | `Consequent`, `Rule`, `RuleBase.validate()` |
| `fuzzification` | `Fuzzifier` → `FuzzificationResult` |
| `inference` | `InferenceMethod`, `MamdaniInference`, `RuleActivation`, `OutputDistribution` |
| `defuzzification` | `Defuzzifier`, `Centroid`, `Bisector`, `MeanOfMaximum`, `DEFUZZIFIERS` |
| `system` | `FuzzySystem`, `FuzzySystemBuilder`, `EvaluationResult` |
| `pipeline` | `FuzzyPipeline`, `PipelineResult` |
| `explanation` | `explain_result`, `explain_pipeline`, `explain_activations` |
| `dsl` | `tokenize`, `parse_formula`, `parse_rule`, syntaxes `ENGLISH` / `FRENCH` |
| `loaders` | `load_system`, `load_system_from_dict`, `load_library`, `load_pipeline` |
| `exceptions` | `FuzzyEngineError` ⊃ `DefinitionError`, `KnowledgeBaseError`, `ParseError`, `EvaluationError` |

## 4.2 Fonctions d'appartenance

| `kind` | Paramètres | Définition |
|---|---|---|
| `triangle` | `a ≤ b ≤ c`, `a < c` | 0 hors `[a,c]`, monte linéairement jusqu'à 1 en `b`, redescend |
| `trapezoid` | `a ≤ b ≤ c ≤ d`, `a < d` | plateau à 1 sur `[b,c]` |
| `ramp_up` | `a < b` | 0 avant `a`, 1 après `b` (épaule droite) |
| `ramp_down` | `a < b` | 1 avant `a`, 0 après `b` (épaule gauche) |
| `gaussian` | `mean`, `sigma > 0` | `exp(−(x−mean)² / 2σ²)` |
| `singleton` | `value` | 1 en `value`, 0 ailleurs |

Les paramètres sont validés à la construction (`DefinitionError`). Toute forme nouvelle se déclare
par héritage de `MembershipFunction` (méthodes `__call__` et `parameters`, attribut `kind`) et
ajout dans `MEMBERSHIP_REGISTRY` pour être utilisable depuis TOML.

## 4.3 Opérateurs

| Rôle | Nom (TOML) | Classe | Formule |
|---|---|---|---|
| Famille (∧, ∨, ¬) | `zadeh` | `ZADEH` | min, max, 1−a |
| | `probabilistic` | `PROBABILISTIC` | a·b, a+b−ab, 1−a |
| | `lukasiewicz` | `LUKASIEWICZ` | max(0,a+b−1), min(1,a+b), 1−a |
| Implication | `min` | `MinimumImplication` | min(α, μ) — Mamdani |
| | `product` | `ProductImplication` | α·μ — Larsen |
| Agrégation | `max` | `MaximumSNorm` | max |
| | `probabilistic_sum` | `ProbabilisticSumSNorm` | a+b−ab |
| | `bounded_sum` | `BoundedSumSNorm` | min(1, a+b) |

## 4.4 Langage de règles (DSL)

Grammaire (EBNF ; mots-clés insensibles à la casse, en anglais **ou** en français) :

```
règle        := [ RULE ident ":" ] IF formule THEN conséquent { AND conséquent }
formule      := disjonction
disjonction  := conjonction { OR conjonction }
conjonction  := négation { AND négation }
négation     := NOT négation | primaire
primaire     := "(" formule ")" | atome
atome        := ident ( IS [ NOT ] | N'EST PAS ) [ modificateur ] ident
conséquent   := ident IS ident
```

| Anglais | Français |
|---|---|
| `RULE` | `REGLE`, `RÈGLE` |
| `IF` / `THEN` | `SI` / `ALORS` |
| `AND` / `OR` / `NOT` | `ET` / `OU` / `NON` |
| `IS` / `IS NOT` | `EST` / `N'EST PAS` |
| `very`, `somewhat`, `extremely` | `très`, `assez` (`plutôt`), `extrêmement` |

Priorité : `NOT` > `AND` > `OR` (règles d'élimination des parenthèses du cours). Exemples valides :

```
SI vitesse EST rapide ET age EST jeune ALORS aptitude EST excellente
REGLE T2: SI buts_p90 EST eleve ET tirs_cadres_pct N'EST PAS bonne ALORS technique EST bonne
IF (a IS x OR b IS y) AND NOT c IS z THEN s IS t AND u IS v
SI vitesse EST très rapide ALORS physique EST excellente
```

Les identifiants acceptent lettres Unicode, chiffres, `_`, `-` et apostrophes ; les mots-clés sont
réservés (une variable ne peut pas s'appeler `est`). Les erreurs de syntaxe (`ParseError`)
indiquent ligne et colonne.

API : `parse_rule(text, identifier=None, weight=1.0, description="") -> Rule`,
`parse_formula(text) -> Formula`. Rendu inverse : `rule.render(FRENCH)` / `str(rule)` (anglais).

## 4.5 Format des bases de connaissances (TOML)

```toml
[system]
name = "technique_attaquant"      # obligatoire
description = "…"                  # optionnel
operators = "zadeh"                # optionnel : zadeh | probabilistic | lukasiewicz
implication = "min"                # optionnel : min | product
aggregation = "max"                # optionnel : max | probabilistic_sum | bounded_sum
defuzzifier = "centroid"           # optionnel : centroid | bisector | mom
resolution = 501                   # optionnel : points d'échantillonnage (>= 2)

# Variable définie en ligne…
[[inputs]]
name = "buts_p90"
description = "Buts par 90 minutes"
unit = "buts/90"
universe = [0, 1.5]
[inputs.terms]
faible = { kind = "ramp_down", params = [0.15, 0.35] }
moyen  = { kind = "triangle",  params = [0.25, 0.45, 0.65] }
eleve  = { kind = "ramp_up",   params = [0.55, 0.8] }

# … ou référencée depuis une bibliothèque partagée (DRY)
[[inputs]]
ref = "xg_p90"

[[outputs]]
ref = "technique"

[[rules]]
id = "T1"                          # optionnel (défaut R1, R2, …)
text = "SI buts_p90 EST eleve ET tirs_cadres_pct EST bonne ALORS technique EST excellente"
weight = 1.0                       # optionnel, dans ]0, 1]
description = "Buteur prolifique et adroit"
```

Bibliothèque partagée (`variables.toml`) : une suite de tables `[[variables]]` au même format
qu'une entrée `[[inputs]]` en ligne. Chargement : `load_library(path)` puis
`load_system(path, library=…)` ou `load_pipeline(name, paths, library=…)`.

Toute incohérence est signalée par `KnowledgeBaseError` avec un chemin contextuel, par exemple :
`[technique/attaquant.toml.rules[3]] règle 'T4' invalide : Règle 'T4' : terme inconnu 'elevé' pour
la variable d'entrée 'xg_p90' (termes : faible, moyen, eleve).`

## 4.6 Algorithme d'évaluation

```
evaluate(values):
  1. fuzzification
       pour chaque entrée v : x ← clamp(values[v], univers_v)   (avertissement si modifié)
                              δ(v, t) ← μ_t(x) pour chaque terme t
  2. inférence (Mamdani)
       pour chaque règle r : α_r ← poids_r × truth(antécédent_r, δ, ops)
       pour chaque sortie o : μ_o(y) ← S_r  I(α_r, μ_{t_r}(y))     (r concluant sur o)
  3. défuzzification
       pour chaque sortie o : y*_o ← defuzzify(μ_o, univers_o)
                              libellé_o ← argmax_t μ_t(y*_o)
  4. résultat : entrées utilisées, δ, activations (trace), sorties nettes, lecture linguistique,
     avertissements
```

Cas limites traités :

- **Entrée hors univers** : ramenée à la borne, avertissement conservé dans le résultat.
- **Entrée manquante ou NaN** : `EvaluationError` (le système refuse de deviner).
- **Ensemble de sortie vide** (aucune règle activée, ou terme de sortie plus étroit que le pas
  de la grille, par exemple un `singleton` hors grille) : le défuzzifieur renvoie `None`, le
  système utilise le milieu de l'univers **et** ajoute un avertissement explicite au résultat ;
  les tests de l'application vérifient que les bases livrées couvrent tout l'espace d'entrée
  pour que ce cas ne se produise pas en exploitation.
- **Défuzzification** : échantillonnage régulier de l'univers (`resolution` points) ; le centroïde
  est `Σ y·μ(y) / Σ μ(y)`, la bissectrice coupe l'aire en deux, `mom` moyenne les abscisses du maximum.

## 4.7 Pipelines

`FuzzyPipeline(name, stages)` enchaîne des systèmes : les sorties d'une étape sont ajoutées au
contexte et deviennent disponibles comme entrées des suivantes. Propriétés :

- `required_inputs` : entrées externes (consommées et non produites en amont) ;
- `produced_outputs`, `final_outputs` ;
- validation : noms d'étapes uniques, aucune sortie produite deux fois, aucune étape ne consomme
  une sortie produite par une étape **ultérieure** (un ordre erroné est refusé au chargement).

`PipelineResult` conserve le résultat de chaque étape (`stage(name)`), toutes les sorties, leurs
libellés et les avertissements cumulés.

## 4.8 Explications

`explain_result(result, syntax=FRENCH, limit=5)` produit un compte rendu lisible :

```
Système « demo »
  Entrées :
    vitesse = 90  ->  lente=0.00, moyenne=0.00, rapide=1.00
    age = 20  ->  jeune=1.00, mature=0.00, veteran=0.00
  Règles déclenchées (1/4), par force :
  - [R1] force=1.00 : SI vitesse EST rapide ET age EST jeune ALORS score EST excellent
  Conclusions :
    score = 89.55  (excellent ; faible=0.00, moyen=0.00, bon=0.00, excellent=1.00)
```

Le texte n'utilise que des caractères affichables sur une console Windows (cp1252) ; les
interfaces reconfigurent de toute façon la sortie en UTF-8.

## 4.9 Utilisation programmatique

```python
from fuzzyengine import *

vitesse = LinguisticVariable("vitesse", Universe(0, 100), (
    FuzzySet("lente", RampDown(20, 40)),
    FuzzySet("moyenne", Triangular(30, 50, 70)),
    FuzzySet("rapide", RampUp(60, 80)),
))
score = LinguisticVariable("score", Universe(0, 100), (
    FuzzySet("faible", Trapezoidal(0, 0, 25, 45)),
    FuzzySet("bon", Trapezoidal(55, 75, 100, 100)),
))
system = (
    FuzzySystemBuilder("demo")
    .add_input(vitesse).add_output(score)
    .add_rule(parse_rule("SI vitesse EST rapide ALORS score EST bon", "R1"))
    .add_rule(parse_rule("SI vitesse EST lente ALORS score EST faible", "R2"))
    .build()
)
result = system.evaluate({"vitesse": 72})
print(result.outputs["score"], result.label("score"))
print(explain_result(result))
```
