# Contribuer

1. Créer une branche depuis `main`.
2. Installer l'environnement : `pip install -e ".[api,dev]"`.
3. Développer en respectant les conventions de `docs/07-guide-developpeur.md` (typage strict,
   immutabilité, erreurs localisées, tests contre les abstractions).
4. Avant de pousser : `make check` (ou `ruff format --check`, `ruff check`, `mypy`, `pytest`)
   et, si des bases de connaissances ont changé, `fuzzyscout validate`.
5. Mettre à jour `CHANGELOG.md` et, pour une décision structurante, ajouter un ADR dans `docs/adr/`.
6. Ouvrir une pull request décrivant le besoin, la solution et les tests ajoutés.
