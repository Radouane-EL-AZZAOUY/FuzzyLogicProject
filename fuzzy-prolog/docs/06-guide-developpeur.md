# 6. Guide du développeur

## 6.1 Installation

```bash
cd fuzzy-prolog
py -3.13 -m venv .venv          # Windows (ou python3 -m venv .venv)
.venv\Scripts\activate
pip install -e ".[dev]"
fuzzyprolog examples/famille.pl -q "grand_parent(X, Y)."
identitylink dedupe
```

Python ≥ 3.11, aucune dépendance d'exécution.

## 6.2 Commandes

| Tâche | Commande |
|---|---|
| Tests | `python -m pytest` |
| Couverture | `python -m pytest --cov=src --cov-report=term-missing` |
| Style | `ruff check src tests scripts` / `ruff format src tests scripts` |
| Typage | `mypy` |
| Porte qualité | `make check` |
| Jeu de données | `python scripts/generate_sample_dataset.py` |

## 6.3 Arborescence

```
src/fuzzyprolog/      moteur (voir docs/03 §3.2) + prelude.pl + cli.py
src/identitylink/     domain/ application/ infrastructure/ interfaces/ builtins.py knowledge/ data/
tests/engine/         exemples du cours, parseur, unification, résolution graduée, CLI
tests/linkage/        normalisation, dédoublonnage, métriques, CSV, CLI
examples/             programmes du cours exécutables (famille, humeur, coupe) et flou.pl
docs/                 cette documentation + adr/
```

## 6.4 Conventions

- Code et docstrings en anglais ; messages utilisateur, règles, données et docs en français.
- `mypy --strict` sans `type: ignore` dans `src/` (hors un cas documenté), `ruff` (E, F, W, I,
  N, UP, B, SIM, C4, RUF), 100 colonnes.
- Objets-valeur immuables ; erreurs typées et localisées ; aucun accès réseau.
- Tests : chaque comportement du cours a un test nommé par sa page.

## 6.5 Étendre

**Un prédéfini gradué** (le point d'extension principal) :

```python
from fuzzyprolog import register
from fuzzyprolog.builtins import graded

@register("age_proche/2", LINKAGE_BUILTINS)
def _age_proche(engine, args, subst, degree):
    a, b = (subst.walk(x).value for x in args)
    yield from graded(subst, 1 - abs(a - b) / 5)
```

puis `age_proche(A1, A2)` est utilisable dans `regles.pl`.

**Une règle ou une similarité** : éditer `knowledge/regles.pl` / `similarites.pl` (ou passer
`--rules` / `--similarities`), puis `identitylink evaluate` pour mesurer l'effet.

**Une t-norme** : classe avec `name` et `__call__(a, b)`, ajoutée à `TNORMS`.

**Une directive** : branche dans `Program.apply_directive`.

**Un prédicat de contrôle** : handler dans `engine._CONTROL` (signature de `ControlHandler`).

**Une source de fiches** : classe exposant `all() -> Sequence[PersonRecord]` (port
`RecordRepository`), branchée dans `interfaces/cli.py`.

## 6.6 Déboguer un programme flou

- `fuzzyprolog fichier.pl` ouvre un REPL ; `--explain` montre chaque étape avec ses degrés.
- `with_degree(But, D)` et `best_degree(But, D)` interrogent les degrés depuis Prolog.
- Un résultat inattendu de similarité : `similar(a, b, D)` affiche le degré fermé transitivement.
- `identitylink query` exécute n'importe quelle requête sur la base construite à partir du CSV.
- `--lambda-cut 0` désactive la coupure pour voir toutes les dérivations faibles.

## 6.7 Intégration continue

`.github/workflows/ci.yml` : ruff (format + lint), mypy, pytest avec couverture, sur Python 3.11,
3.12, 3.13 (Linux) et 3.13 (Windows), plus l'exécution des exemples du cours.
