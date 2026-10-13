# ADR-003 — Bases de connaissances déclaratives (TOML) et langage de règles bilingue

**Statut** : accepté — 2026-10-13

## Contexte

Les règles de scouting évoluent souvent (nouveau poste, seuils révisés après une saison). Les
personnes qui les font évoluer ne sont pas nécessairement développeuses. Le format FCL (IEC 61131-7)
existe mais est verbeux et peu outillé en Python.

## Décision

- Décrire variables et règles dans des fichiers **TOML** (lecteur `tomllib` de la bibliothèque
  standard, commentaires, lisible par un humain, validé par Git comme du code).
- Écrire les règles dans un **mini-langage** proche du langage naturel, avec mots-clés en
  **français ou en anglais** (`SI … ALORS`, `IF … THEN`), analysé par un parseur à descente
  récursive dont la grammaire reproduit la priorité des connecteurs du cours.
- Mutualiser les variables dans une **bibliothèque** (`variables.toml`) référencée par `ref =`.

## Conséquences

- (+) Ajouter un poste ou ajuster un seuil ne demande aucun code Python ; la validation au
  chargement localise précisément les erreurs.
- (+) Les règles se lisent telles quelles dans les explications fournies à l'utilisateur.
- (−) Un format maison implique de maintenir le parseur et sa documentation (grammaire EBNF dans
  `docs/04`). Le coût est contenu : ~150 lignes, entièrement testées.
