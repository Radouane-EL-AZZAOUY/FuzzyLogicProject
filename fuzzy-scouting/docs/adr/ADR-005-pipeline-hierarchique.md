# ADR-005 — Évaluation hiérarchique (technique, physique, profil → aptitude)

**Statut** : accepté — 2026-10-13

## Contexte

Un poste dépend d'une dizaine de statistiques. Une base de règles plate couvrant toutes les
combinaisons de 3 termes sur 10 variables compterait jusqu'à `3¹⁰ = 59 049` règles : impossible à
rédiger, relire ou expliquer.

## Décision

Décomposer l'évaluation en un **pipeline** de petits systèmes (`fuzzyengine.pipeline`) :

1. `technique/<poste>` : 3-4 statistiques spécifiques au poste → `technique` ;
2. `physique/<famille>` : vitesse, volume de course, jeu aérien, taille → `physique` ;
3. `profil/commun` : âge, temps de jeu, blessures → `profil` ;
4. `aptitude/commun` : `technique`, `physique`, `profil` → `aptitude`.

Les scores intermédiaires partagent la même échelle `[0, 100]` et les mêmes termes, ce qui les rend
composables. Chaque étape compte 8 à 16 règles, dont des **règles de couverture** à faible poids
garantissant qu'au moins une règle s'active en tout point de l'espace d'entrée (vérifié par test).

## Conséquences

- (+) ~60 règles au total par poste au lieu de dizaines de milliers ; chaque étape est lisible et
  justifiable ; les étapes 2-4 sont partagées entre postes (DRY).
- (+) Le rapport d'évaluation expose les scores intermédiaires, ce qui est précisément ce qu'un
  recruteur veut lire (« technique excellente mais profil à risque »).
- (−) L'ordre des étapes est figé par le catalogue des postes ; les interactions croisées entre
  statistiques de familles différentes doivent passer par les scores intermédiaires.
