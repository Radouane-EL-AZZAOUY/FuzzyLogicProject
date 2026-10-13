# ADR-001 — Un moteur en Python pur, sans dépendance externe

**Statut** : accepté — 2026-10-13

## Contexte

Des bibliothèques existantes (scikit-fuzzy, simpful) implémentent l'inférence floue. Le projet
est à la fois académique (il doit rendre visibles les notions du cours) et destiné à la
pré-production (il doit être simple à installer, auditer et maintenir).

## Décision

Écrire `fuzzyengine` en Python standard (`dataclasses`, `tomllib`, `math`), sans NumPy ni
bibliothèque floue tierce. Les dépendances externes sont cantonnées à l'extra `[api]` (FastAPI,
pydantic, uvicorn) et à l'outillage de développement.

## Conséquences

- (+) Chaque notion du cours correspond à une classe lisible (`Atom`, `Interpretation`, `Rule`…)
  plutôt qu'à des tableaux NumPy ; le code est le support pédagogique.
- (+) Installation triviale, exécutable partout où Python ≥ 3.11 est présent (dont des conteneurs
  minimaux), surface d'attaque et de maintenance réduites.
- (−) Les performances sont celles de Python pur (≈ 4 ms par évaluation à 4 étapes). Suffisant
  pour des effectifs de quelques milliers de joueurs ; une implémentation vectorisée du
  `Defuzzifier` reste possible derrière la même interface si le besoin apparaît.
