# 1. Problème et objectifs

## 1.1 Le besoin métier

Un club de football professionnel renouvelle chaque saison plusieurs postes. Sa cellule de
recrutement dispose de bases de données de centaines, voire de milliers de joueurs, décrits par des
dizaines de statistiques normalisées « par 90 minutes » (buts, buts attendus, passes
progressives, duels aériens, vitesse de pointe…), auxquelles s'ajoutent l'âge, le temps de jeu, les
blessures et la valeur marchande.

La question que pose un directeur sportif est simple à formuler et difficile à automatiser :

> « Quels sont les meilleurs candidats pour **ce** poste, compte tenu de **notre** budget et de
> **notre** politique d'âge — et pourquoi ? »

Trois obstacles :

1. **Les critères sont vagues.** Un recruteur parle de joueur « rapide », « adroit devant le but »,
   « mûr mais pas vétéran ». Fixer un seuil net (rapide ⇔ ≥ 34,0 km/h) classe différemment deux
   joueurs quasi identiques et oblige à des arbitrages artificiels.
2. **Les critères se combinent.** « Un attaquant qui marque beaucoup *malgré* une adresse moyenne
   reste bon ; un attaquant qui ne marque pas *bien qu'il* se procure beaucoup d'occasions est à
   surveiller. » Ce sont des règles d'expertise, pas des pondérations linéaires.
3. **La décision doit être justifiable.** Un classement non expliqué n'est pas utilisable dans une
   réunion de recrutement ; un modèle statistique opaque est écarté par les praticiens.

## 1.2 Pourquoi la logique floue

| Approche | Vague | Combinaisons expertes | Explicable | Données requises |
|---|---|---|---|---|
| Tableur à seuils | non | partiellement | oui | aucune |
| Score linéaire pondéré | non | non | partiellement | aucune |
| Apprentissage automatique | implicite | implicite | **non** | historique étiqueté (rare, biaisé) |
| **Système expert flou** | **oui** | **oui** (règles SI/ALORS) | **oui** (règles activées) | **aucune** (connaissance experte) |

La logique floue est l'outil conçu pour ce cas : elle formalise des prédicats gradués, combine des
règles linguistiques avec des opérateurs logiques rigoureux et produit une conclusion accompagnée de
sa dérivation. Elle s'inscrit dans l'IA symbolique étudiée en cours (représentation de
connaissances, systèmes formels, inférence) et en constitue une extension naturelle.

## 1.3 Objectifs

| # | Objectif | Critère de succès (vérifié) |
|---|---|---|
| O1 | Évaluer un joueur pour un poste avec un score et un libellé linguistique | `fuzzyscout evaluate` ; tests `test_use_cases.py` |
| O2 | Classer un effectif pour un poste sous contraintes nettes (budget, âge, minutes, nationalité, poste naturel) | `fuzzyscout rank` ; exclusions motivées |
| O3 | Expliquer chaque verdict par les règles activées et les degrés mesurés | `--explain`, champ `etapes` de l'API |
| O4 | Permettre à un expert métier de modifier les règles sans coder | bases TOML, validation au chargement, DSL français/anglais |
| O5 | Rester aligné sur le cours de logique (fbf, interprétation, modus ponens, système formel) | chapitre 2, tests des propriétés logiques |
| O6 | Architecture lisible, maintenable, extensible et déployable | chapitres 3, 7, 8 ; 96 % de couverture ; Docker ; typage strict |
| O7 | Démontrer que le moteur résout aussi un autre problème réel | application `fuzzyirrigation` (économie d'eau) |

## 1.4 Périmètre

**Inclus** : cinq postes (gardien, défenseur central, milieu central, ailier, attaquant) ; un
format de données CSV documenté ; une CLI ; une API HTTP ; une base de connaissances complète et
validée ; un jeu de données synthétique de démonstration ; documentation et tests.

**Exclus (et pourquoi)** :

- *Collecte de données réelles* : les fournisseurs (Opta, StatsBomb, Wyscout, FBref) ont des
  licences propres ; le projet définit le format d'entrée et fournit des données synthétiques
  reproductibles. Brancher une source réelle = un adaptateur (`PlayerRepository`).
- *Apprentissage des règles ou des fonctions d'appartenance* : la connaissance est explicitement
  rédigée ; un réglage automatique (neuro-flou) est une extension possible, non nécessaire pour
  l'objectif d'explicabilité.
- *Authentification de l'API* : l'API est conçue pour tourner derrière une passerelle qui s'en charge
  (chapitre 8).

## 1.5 Parties prenantes et usages

| Acteur | Usage | Interface |
|---|---|---|
| Directeur sportif / recruteur | Classement d'un effectif pour un poste, lecture des explications | CLI (`rank`, `evaluate`), rapports JSON |
| Analyste données | Alimentation du CSV, analyses « et si » (`--attr`), intégration dans un tableau de bord | API HTTP |
| Expert métier (entraîneur, scout senior) | Révision des règles et des seuils | fichiers TOML + `fuzzyscout validate` |
| Développeur | Extension (postes, sources de données, interfaces) | guide du développeur |

## 1.6 Hypothèses

- Les statistiques sont normalisées par 90 minutes et proviennent d'une saison de référence
  comparable entre joueurs (même niveau de compétition ou coefficient appliqué en amont).
- Les univers de discours et les seuils des termes linguistiques (chapitre 5) traduisent des ordres
  de grandeur usuels ; ils sont destinés à être ajustés par les experts du club, ce que le format
  déclaratif rend trivial.
- Un joueur dont il manque une statistique requise est **exclu avec motif** plutôt qu'évalué sur une
  valeur devinée : le système préfère ne rien dire plutôt que de dire faux.
