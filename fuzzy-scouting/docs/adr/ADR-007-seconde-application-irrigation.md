# ADR-007 — Une seconde application (irrigation) pour prouver la généricité du moteur

**Statut** : accepté — 2026-10-13

## Contexte

Le cahier des charges exige que le projet résolve un problème réel. Le scouting assisté répond à
un besoin concret des cellules de recrutement, mais son « réalisme » dépend de données que le
projet ne fournit qu'en version synthétique. Par ailleurs, un moteur n'est générique que s'il a
au moins deux clients.

## Décision

Livrer une seconde application, `fuzzyirrigation` : un contrôleur flou qui recommande une durée
d'arrosage à partir de l'humidité du sol, de la température, de l'humidité de l'air et de la pluie
prévue — un problème d'économie d'eau concret dans un contexte de stress hydrique. Elle réutilise
le moteur sans modification, avec une base de connaissances de 13 règles et une couche domaine de
trois classes.

## Conséquences

- (+) Démonstration que l'ajout d'un domaine = une base TOML + un domaine mince ; le type de
  sortie diffère (action de commande en minutes vs score de classement), ce qui exerce le moteur
  différemment.
- (+) Second jeu de tests indépendant du scouting.
- (−) Périmètre volontairement réduit (pas d'API HTTP, pas de persistance) : il s'agit d'une
  preuve d'architecture, documentée comme telle.
