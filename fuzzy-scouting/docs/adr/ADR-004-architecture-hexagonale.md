# ADR-004 — Architecture hexagonale pour l'application de scouting

**Statut** : accepté — 2026-10-13

## Contexte

L'application doit être livrée en CLI et en API HTTP, lire aujourd'hui un CSV et demain une base
de données ou l'API d'un fournisseur de statistiques, et rester testable sans fichiers ni réseau.

## Décision

Organiser `fuzzyscout` en quatre couches à dépendances orientées vers l'intérieur :
`domain` (entités, objets-valeur, ports sous forme de `Protocol`, service `evaluate_player`),
`application` (cas d'utilisation `EvaluatePlayer`, `RankPlayers`, façade `ScoutingService`),
`infrastructure` (adaptateurs CSV/TOML/mémoire), `interfaces` (CLI, API, présentation). Le
câblage concret est isolé dans `bootstrap.py`.

## Conséquences

- (+) Les cas d'utilisation se testent avec des dépôts en mémoire ; CLI et API partagent le même
  service et la même présentation (aucune divergence de comportement).
- (+) Remplacer une source de données = un adaptateur + une ligne dans `bootstrap.py`.
- (−) Plus de fichiers qu'un script monolithique ; compensé par des modules courts (< 150 lignes)
  et une arborescence qui nomme explicitement chaque responsabilité.
