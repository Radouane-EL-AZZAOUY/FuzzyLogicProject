# ADR-006 — Contraintes nettes (filtres) séparées des préférences floues (règles)

**Statut** : accepté — 2026-10-13

## Contexte

Certaines exigences d'un recrutement sont binaires : budget maximal, âge limite imposé par la
politique du club, nationalité (quotas), temps de jeu minimal pour que les statistiques soient
significatives. Les encoder dans des règles floues les rendrait négociables, ce qu'elles ne sont pas.

## Décision

Modéliser ces exigences comme des **filtres nets** (`domain/filters.py::RankingFilters`),
appliqués avant l'inférence. Un joueur filtré apparaît dans le rapport comme **exclu avec une
raison explicite** ; un joueur sans les statistiques requises est également exclu (raison :
statistiques manquantes). Les préférences graduées (vitesse, finition, maturité…) restent dans
les règles floues.

## Conséquences

- (+) Le rapport distingue clairement « non éligible » de « éligible mais faible ».
- (+) Les filtres sont triviaux à tester et à étendre (un champ + une condition).
- (−) Un critère pourrait être tantôt net, tantôt flou selon le club (ex. budget avec marge) ; le
  cas échéant, ajouter une variable `valeur_marche_meur` à une base de règles reste possible.
