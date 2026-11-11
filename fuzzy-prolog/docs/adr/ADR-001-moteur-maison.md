# ADR-001 — Écrire un moteur de Prolog flou plutôt qu'utiliser un Prolog existant

**Statut** : accepté — 2026-10-13

## Contexte

Des systèmes de Prolog flou existent (Bousi~Prolog sur SWI-Prolog, FLOPER, Ciao Fuzzy Prolog),
mais ils nécessitent une installation Prolog externe, sont peu maintenus ou imposent leur propre
sémantique. Le projet doit rester un livrable Python autonome, lisible par un étudiant du cours, et
chaque notion du support (unification p. 56, résolution p. 60, backtracking p. 80, coupe p. 82)
doit être visible dans le code.

## Décision

Implémenter le moteur en Python pur, module par module, en suivant l'ordre des notions du cours,
avec un langage proche du Prolog standard enrichi de `@` (degré) et `~` (similarité).

## Conséquences

- (+) Correspondance directe cours ↔ code ; aucune dépendance ; tests qui rejouent le support.
- (+) Point d'extension natif en Python (prédéfinis gradués) pour l'application.
- (−) Sous-ensemble de Prolog (pas d'`assert`, de modules…) et performances d'un interpréteur
  Python (≈ 20 µs par étape de résolution) ; suffisant pour les bases de règles métier et des
  milliers de faits, documenté dans le chapitre 4.
