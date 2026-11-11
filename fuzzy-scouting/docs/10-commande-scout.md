# 10. Système de commande Scout

Un second système d'inférence, à côté de l'évaluation par poste : il attribue à un joueur un
**niveau de 1 à 6** à partir de trois variables linguistiques — **vitesse**, **accélération**,
**tacle** — qui ne sont pas saisies mais **déduites** d'autres mesures, lesquelles peuvent être
précises ou floues.

## 10.1 Correspondance avec le cahier des charges

| Exigence | Réalisation |
|---|---|
| Trois variables linguistiques : vitesse (fort, moyenne, faible), accélération, tacle | Variables `vitesse`, `acceleration`, `tacle` de `knowledge/variables.toml`, toutes sur l'échelle 0–100 avec les termes `faible`, `moyenne`, `fort` |
| Définir les règles | Quatre bases de 27 règles dans `knowledge/commande/` (108 règles) : `vitesse.toml`, `acceleration.toml`, `tacle.toml`, `niveau.toml` |
| fort-fort-fort → niveau 6 | Règle `N1` de `niveau.toml` ; c'est la seule combinaison qui conclut au niveau 6 |
| Chaque variable est déduite d'autres variables | Une étape d'inférence par variable (§ 10.2) |
| Accélération déduite de la vitesse de changement, de la distance de déplacement et du temps de réaction | Entrées de `acceleration.toml` : `vitesse_changement_ms2`, `distance_deplacement_m`, `temps_reaction_s` |
| Une valeur précise ou floue (intervalle ou catégorie) | Trois formes d'observation acceptées par le moteur (§ 10.4) |
| Cas 1 : un seul joueur | Onglet « Commande Scout » → *Un joueur* ; `fuzzyscout level --obs …` ou `--player ID` ; `POST /commande/evaluations` |
| Cas 2 : jeu de données des joueurs d'un même poste | Onglet « Commande Scout » → *Joueurs d'un même poste* ; `fuzzyscout level --position CODE` ; `POST /commande/classements` |

Deux points du cahier des charges étaient ouverts ; les choix retenus sont des hypothèses, isolées
dans les fichiers TOML et donc modifiables sans toucher au code :

- les mesures dont se déduisent la **vitesse** et le **tacle** (seules celles de l'accélération
  étaient données) ;
- le niveau des 26 combinaisons autres que fort-fort-fort (§ 10.3).

## 10.2 Architecture : trois déductions, puis une décision

```
vitesse de pointe ─┐
temps sur 30 m ────┼─► [commande_vitesse]      ─► vitesse ──────┐
sprints / 90 min ──┘                                            │
vitesse de changement ─┐                                        │
distance de déplacement┼─► [commande_acceleration] ─► accélération ─┼─► [commande_niveau] ─► niveau 1…6
temps de réaction ─────┘                                        │
tacles / 90 min ───┐                                            │
tacles réussis % ──┼─► [commande_tacle]        ─► tacle ────────┘
fautes / 90 min ───┘
```

| Variable déduite | Mesure | Univers | Termes (favorable → défavorable) |
|---|---|---|---|
| vitesse | `vitesse_max_kmh` — vitesse de pointe | 25–38 km/h | rapide, moyenne, lente |
| | `temps_30m_s` — temps sur 30 m lancé | 3,5–5,5 s | court, moyen, long |
| | `sprints_p90` — sprints (> 25 km/h) par 90 min | 0–40 | eleve, moyen, faible |
| accélération | `vitesse_changement_ms2` — variation de vitesse au démarrage | 0–8 m/s² | elevee, moyenne, faible |
| | `distance_deplacement_m` — distance en 2 s, départ arrêté | 4–14 m | longue, moyenne, courte |
| | `temps_reaction_s` — temps de réaction à un signal | 0,1–0,6 s | court, moyen, long |
| tacle | `tacles_p90` — tacles par 90 min | 0–6 | eleve, moyen, faible |
| | `tacles_reussis_pct` — taux de tacles réussis | 0–100 % | eleve, moyen, faible |
| | `fautes_p90` — fautes commises par 90 min | 0–4 | faible, moyen, eleve |

Le système est un `FuzzyPipeline` de quatre étapes, construit par
`TomlPipelineProvider.command_pipeline()`. Il réutilise tel quel le moteur `fuzzyengine` (langage
de règles, inférence de Mamdani, centroïde) et la bibliothèque de variables partagée.

## 10.3 Barème des règles

Chaque étape couvre les 3 × 3 × 3 = **27 combinaisons** de ses entrées : quelle que soit
l'observation, au moins une règle se déclenche. Les conclusions suivent un barème unique, simple à
justifier : une entrée favorable vaut 2 points, intermédiaire 1 point, défavorable 0 point.

| Total | Variable déduite (étapes 1 à 3) | Niveau (étape 4) | Combinaisons |
|---|---|---|---|
| 6 | fort | **niveau 6** | 1 (fort, fort, fort) |
| 5 | fort | niveau 5 | 3 |
| 4 | fort | niveau 4 | 6 |
| 3 | moyenne | niveau 3 | 7 |
| 1 ou 2 | faible | niveau 2 | 9 |
| 0 | faible | niveau 1 | 1 |

La sortie `niveau` a pour univers [0, 7] et six termes triangulaires `niveau_1` … `niveau_6`,
chacun centré sur son niveau (`triangle(k−1, k, k+1)`). Le centroïde donne une valeur réelle
(par exemple 5,57) qui sert à **classer** les joueurs ; le niveau affiché est l'entier le plus
proche, borné à [1, 6].

## 10.4 Observations précises ou floues

Le fuzzifieur accepte, pour chaque entrée, une *observation* (`fuzzyengine.observations`) :

| Forme | Écriture (CSV, CLI, JSON) | Degré de chaque terme *T* |
|---|---|---|
| Valeur précise | `4.12` | μ_T(x) — fuzzification classique |
| Intervalle | `4.0..4.3`, `[4.0 ; 4.3]`, JSON `[4.0, 4.3]` ou `{"min": 4.0, "max": 4.3}` | sup { μ_T(x) : x ∈ [a, b] } |
| Catégorie | `court` | 1 pour le terme cité, 0 pour les autres |
| Degrés explicites | JSON `{"fort": 0.7, "moyenne": 0.3}` | ceux qui sont donnés |

L'intervalle est traité selon la théorie des possibilités : le degré d'un terme est la meilleure
appartenance atteignable dans l'intervalle. La valeur précise en est le cas particulier `a = b`, et
élargir un intervalle ne peut qu'augmenter les degrés (propriétés vérifiées par les tests). Le
supremum est exact pour les formes linéaires par morceaux : il est évalué aux bornes, aux points de
rupture de la forme et sur une grille de sécurité. Une catégorie inconnue de la variable est
refusée avec la liste des catégories possibles.

## 10.5 Chaînage flou entre les étapes

Les pipelines par poste transmettent un **nombre** d'une étape à la suivante (défuzzification, puis
re-fuzzification). Le système de commande utilise l'autre mode, `chaining = "fuzzy"` : l'étape
finale reçoit la **conclusion floue** elle-même, c'est-à-dire le degré auquel les règles ont conclu
chaque terme (`vitesse : moyenne 0,25, fort 0,33`). Rien n'est perdu entre les deux niveaux, et la
variable intermédiaire reste une *catégorie graduée*, comme le demande le cahier des charges. Le
score sur 100 de chaque variable déduite est tout de même calculé, pour l'affichage uniquement.

Exemple (joueur `P036`, `fuzzyscout level --player P036 --explain`) :

```
Niveau : 6 / 6 (valeur 5.57)
Variables déduites : vitesse=67 (fort) | acceleration=81 (fort) | tacle=82 (fort)
  Étape « commande_tacle »
    tacles_p90 = 1.2 -> faible=0.75, moyen=0.00, eleve=0.00
    tacles_reussis_pct = [79 ; 91] -> faible=0.00, moyen=0.00, eleve=1.00
    fautes_p90 = 0.6 -> faible=1.00, moyen=0.00, eleve=0.00
    - [T19] force=0.75 : SI tacles_p90 EST faible ET tacles_reussis_pct EST eleve ET fautes_p90 EST faible ALORS tacle EST fort
    => tacle : fort=0.75
  Étape « commande_niveau »
    vitesse : faible=0.00, moyenne=0.25, fort=0.33 (conclusion de l'étape précédente)
    acceleration : faible=0.00, moyenne=0.00, fort=0.60 (conclusion de l'étape précédente)
    tacle : faible=0.00, moyenne=0.00, fort=0.75 (conclusion de l'étape précédente)
    - [N1] force=0.33 : SI vitesse EST fort ET acceleration EST fort ET tacle EST fort ALORS niveau EST niveau_6
    - [N10] force=0.25 : SI vitesse EST moyenne ET acceleration EST fort ET tacle EST fort ALORS niveau EST niveau_5
    => niveau : niveau_5=0.25, niveau_6=0.33
```

## 10.6 Utilisation

**Interface web** — onglet « Commande Scout » :

- *Un joueur* (cas 1) : pour chacune des neuf mesures, choisir sa forme (valeur, intervalle,
  catégorie) ; le niveau, les trois variables déduites et le raisonnement se mettent à jour en
  direct. « Partir d'un joueur » reprend les observations d'un joueur du jeu de données.
- *Joueurs d'un même poste* (cas 2) : classement des joueurs du poste par niveau ; un clic ouvre
  le raisonnement complet du joueur.
- *Règles du système* : le barème, les 108 règles en clair et les fonctions d'appartenance.

**Ligne de commande** :

```bash
# Cas 1 — un joueur du jeu de données, avec l'explication
fuzzyscout level --player P036 --explain

# Cas 1 — un joueur libre : valeurs, intervalles et catégories mélangés
fuzzyscout level --obs vitesse_max_kmh=34.6 --obs temps_30m_s=4.0..4.3 --obs sprints_p90=eleve \
  --obs vitesse_changement_ms2=5.2 --obs distance_deplacement_m=10.5..11.5 \
  --obs temps_reaction_s=court --obs tacles_p90=2.9 --obs tacles_reussis_pct=72 --obs fautes_p90=faible

# Cas 2 — les joueurs d'un même poste
fuzzyscout level --position attaquant
```

**API HTTP** :

| Méthode | Route | Corps | Réponse |
|---|---|---|---|
| GET | `/commande` | — | étapes, règles, variables (courbes échantillonnées) |
| POST | `/commande/evaluations` | `{"observations": {mesure: observation}, "name"?, "trace"?}` | niveau, variables déduites, observations, étapes |
| GET | `/commande/joueurs/{id}` | — | évaluation d'un joueur du jeu de données (404 si inconnu, 422 si une mesure manque) |
| POST | `/commande/classements` | `{"position"?: code, "limit"?: n}` | joueurs du poste classés par niveau, et joueurs non évaluables avec la raison |

## 10.7 Données

Les observations des joueurs sont lues dans un fichier CSV distinct du fichier des joueurs
(`data/observations_commande.csv`, ou `--observations` / `FUZZYSCOUT_OBSERVATIONS_CSV`) : une
colonne `id`, puis une colonne par mesure. Une cellule contient une valeur, un intervalle
(`4.0..4.3`) ou une catégorie (`court`) ; une cellule vide signifie « non observé ». Les
observations de ce fichier complètent les statistiques du fichier des joueurs et priment sur
elles. Un joueur auquel il manque une mesure n'est pas évalué ; il est listé avec la raison.

Le fichier d'exemple est **synthétique** (`scripts/generate_command_observations.py`, graine fixe) :
40 joueurs, dont environ une cellule sur cinq est volontairement un intervalle ou une catégorie.

## 10.8 Limites

- Les seuils des fonctions d'appartenance sont des ordres de grandeur plausibles, non calibrés sur
  des mesures réelles.
- Le barème donne le même poids aux trois mesures d'une variable et aux trois variables.
- Une catégorie est tenue pour entièrement vraie : un jugement hésitant s'exprime par des degrés
  explicites ou par un intervalle.
- Le système ne dépend pas du poste : un gardien est jugé sur les mêmes mesures qu'un défenseur.
  La comparaison n'a de sens qu'entre joueurs d'un même poste (cas 2).
