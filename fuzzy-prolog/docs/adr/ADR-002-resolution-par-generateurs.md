# ADR-002 — Résolution SLD par générateurs Python

**Statut** : accepté — 2026-10-13

## Contexte

Le cours décrit la recherche de Prolog comme un parcours en profondeur avec retour arrière au
dernier point de choix (p. 79-80). Deux implémentations sont possibles : une machine à états
explicite (pile de points de choix, *trail*) ou des générateurs imbriqués.

## Décision

Chaque étape de résolution est un générateur : reprendre le générateur, c'est revenir en arrière.
Les substitutions sont immuables (copie à chaque liaison), donc aucun *trail* n'est nécessaire.
Le coupe-choix est un signal `_CutDone(barrière)` qui remonte les générateurs jusqu'à la clause
propriétaire.

## Conséquences

- (+) Le code se lit comme la description du cours ; la coupe, `call/1`, la négation et
  `findall/3` tiennent en quelques lignes.
- (−) La profondeur d'une dérivation est bornée par la pile Python : `max_depth` (1 000 par
  défaut) lève `DepthLimitError` avant `RecursionError`. Les listes longues (> ~1 000 éléments)
  ou les récursions profondes sortent du périmètre, ce qui est acceptable pour des règles métier.
- (−) La copie des substitutions coûte O(n) par liaison (la trace, elle, est une liste chaînée
  persistante) ; négligeable pour des dérivations courtes, à revoir (structures persistantes,
  *trail*) si le moteur devait servir d'interpréteur général. `max_depth` borne la longueur
  d'une dérivation (nombre de buts résolus), ce que dit son message d'erreur.
