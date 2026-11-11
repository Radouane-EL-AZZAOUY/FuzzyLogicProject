# ADR-005 — Règles métier en Prolog flou, mesures numériques en prédéfinis Python

**Statut** : accepté — 2026-10-13

## Contexte

Le rapprochement combine un raisonnement symbolique (quelles preuves suffisent ?) et des mesures
numériques (distance entre deux chaînes, entre deux dates). Tout mettre en Prolog rendrait les
mesures illisibles ; tout mettre en Python ferait disparaître l'explicabilité des règles.

## Décision

- Les **décisions** (`meme_personne/2`, règles R1-R3, négations, degrés de confiance) et les
  **alias** (`similarites.pl`) sont en Prolog flou, modifiables sans code.
- Les **mesures** (`nom_similaire/2`, `date_proche/2`, `tel_similaire/2`) sont des prédéfinis
  gradués Python, testés unitairement, qui réussissent avec un degré.
- Le moteur ignore le domaine : les prédéfinis sont enregistrés dans un registre privé passé à
  `Engine(builtins=…)`.

## Conséquences

- (+) Un expert métier lit et modifie les règles ; un développeur maintient les mesures.
- (+) L'explication montre les deux : la règle et le degré de chaque mesure.
- (−) Deux langages à maintenir ; la frontière doit rester nette (un prédéfini ne décide pas, il
  mesure).
