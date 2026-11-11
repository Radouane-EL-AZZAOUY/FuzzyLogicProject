# 7. Guide du développeur

## 7.1 Prérequis et installation

- Python **3.11 ou plus** (le cœur utilise `tomllib`, `dataclass(slots=True)`, `itertools.pairwise`).
- Aucune dépendance système. `make` est facultatif.

```bash
git clone <dépôt> && cd fuzzy-scouting
python -m venv .venv
.venv\Scripts\activate                # Windows
source .venv/bin/activate             # Linux / macOS
python -m pip install --upgrade pip
pip install -e ".[api,dev]"
```

> **Windows** : si plusieurs Python sont installés (QGIS, Anaconda…), créer le venv avec le
> lanceur officiel : `py -3.13 -m venv .venv`. Les commandes `fuzzyscout` et `fuzzyirrigation` sont
> disponibles dans le venv après l'installation éditable.

## 7.2 Commandes courantes

Sans `make` (Windows notamment), le lanceur `scout` couvre l'essentiel : `scout` (interface web),
`scout setup`, `scout test`, `scout check`, `scout demo` — `./scout.sh …` sous Linux/macOS.

| Tâche | `make` | Équivalent direct |
|---|---|---|
| Tests | `make test` | `python -m pytest` |
| Tests + couverture | `make cov` | `python -m pytest --cov=src --cov-report=term-missing` |
| Style | `make lint` / `make format` | `ruff check src tests scripts` / `ruff format src tests scripts` |
| Typage strict | `make typecheck` | `mypy` |
| Porte qualité complète | `make check` | les quatre ci-dessus |
| Régénérer les données | `make data` | `python scripts/generate_sample_players.py` |
| Démo | `make demo` | `fuzzyscout rank --position attaquant --top 10 --explain` |
| API locale | `make api` | `fuzzyscout serve` |

La porte qualité (`make check`) doit être verte avant toute livraison : format, lint, mypy
strict, tests.

## 7.3 Arborescence et responsabilités

```
src/fuzzyengine/              moteur générique — ne connaît ni joueurs ni parcelles
  exceptions.py               hiérarchie d'erreurs (FuzzyEngineError)
  universe.py  membership.py  variables.py          définitions (ensembles flous)
  operators.py modifiers.py   formulas.py           logique (connecteurs, fbf, interprétation)
  rules.py     fuzzification.py inference.py        règles, fuzzification, modus ponens généralisé
  defuzzification.py system.py pipeline.py          conclusion nette, système, chaînage
  explanation.py              traces lisibles
  dsl/   syntax.py lexer.py parser.py               langage de règles FR/EN
  loaders/ toml_loader.py                           TOML -> FuzzySystem / FuzzyPipeline / bibliothèque
src/fuzzyscout/
  domain/        player.py position.py filters.py evaluation.py evaluator.py ports.py errors.py
  application/   evaluate_player.py rank_players.py scouting_service.py
  infrastructure/ csv_player_repository.py toml_position_catalog.py toml_pipeline_provider.py memory.py resources.py
  interfaces/    cli.py presenters.py api/{app.py, schemas.py}
  knowledge/     variables.toml positions.toml technique/ physique/ profil/ aptitude/
  data/          joueurs_exemple.csv
  config.py bootstrap.py
src/fuzzyirrigation/          domain.py advisor.py cli.py knowledge/irrigation.toml
tests/                        engine/ scouting/ irrigation/ (+ conftest.py avec un système témoin)
scripts/generate_sample_players.py
docker/                       Dockerfile docker-compose.yml
```

## 7.4 Conventions

- **Langues** : identifiants, docstrings et messages de journal en anglais (convention de l'industrie,
  code réutilisable) ; messages d'erreur destinés aux utilisateurs, règles, données et documentation
  en français (public du projet).
- **Typage** : `from __future__ import annotations`, annotations complètes, `mypy --strict` sans
  `type: ignore` dans `src/` (deux exceptions documentées dans les tests).
- **Immutabilité** : `@dataclass(frozen=True, slots=True)` pour les objets-valeur ; les collections
  exposées sont des tuples ou des vues en lecture seule.
- **Erreurs** : toujours une sous-classe de `FuzzyEngineError` (moteur) ou `ScoutingError`
  (application), avec un message localisant le problème (fichier, règle, colonne, ligne). Les
  interfaces convertissent ces erreurs en code de retour 1 ou en réponse HTTP 4xx.
- **Style** : `ruff` (règles E, F, W, I, N, UP, B, SIM, C4, RUF), 100 colonnes, `ruff format`.
- **Tests** : `pytest`, un fichier par module ou par préoccupation, fixtures partagées dans
  `conftest.py`, pas d'accès réseau, données temporaires via `tmp_path`.
- **Commits** : messages à l'impératif, un sujet par commit ; `CHANGELOG.md` mis à jour par version.

## 7.5 Comment étendre

### Ajouter un poste (aucun code)

1. Créer `knowledge/technique/<poste>.toml` sur le modèle de `technique/ailier.toml` : référencer
   les variables existantes (`ref = "…"`) ou en ajouter dans `variables.toml`.
2. Déclarer le poste dans `knowledge/positions.toml` avec ses quatre étapes.
3. `fuzzyscout validate` : la base est chargée, chaque règle vérifiée (variables, termes, poids).
4. Ajouter le poste à `EXPECTED_POSITIONS` dans `tests/scouting/test_knowledge.py` : le test de
   couverture de l'espace d'entrée s'appliquera automatiquement.

### Ajouter une statistique

1. Nouvelle colonne dans le CSV (nom = nom de variable).
2. Nouvelle entrée `[[variables]]` dans `variables.toml` (univers + termes recouvrants).
3. L'utiliser dans les règles ; `validate` signale toute faute de frappe.

### Ajouter une forme de fonction d'appartenance

```python
@dataclass(frozen=True, slots=True)
class Sigmoid(MembershipFunction):
    center: float
    slope: float
    kind: ClassVar[str] = "sigmoid"
    def __call__(self, x: float) -> float: ...
    def parameters(self) -> tuple[float, ...]: return (self.center, self.slope)

MEMBERSHIP_REGISTRY["sigmoid"] = Sigmoid   # utilisable dans TOML : kind = "sigmoid"
```

### Ajouter une méthode de défuzzification, une famille d'opérateurs, une inférence

Même principe : implémenter l'abstraction (`Defuzzifier`, `BinaryOperator`/`UnaryOperator`,
`InferenceMethod`) et l'enregistrer dans `DEFUZZIFIERS`, `OPERATOR_FAMILIES` / `IMPLICATIONS` /
`AGGREGATIONS`, ou l'injecter dans `FuzzySystem(inference=…)`. Les tests du moteur sont écrits
contre les abstractions et servent de spécification.

### Brancher une autre source de joueurs

```python
class SqlPlayerRepository:                      # aucun héritage requis (Protocol)
    def all(self) -> Sequence[Player]: ...
    def get(self, identifier: str) -> Player: ...   # lève PlayerNotFoundError
```

puis dans `bootstrap.py` : `players=SqlPlayerRepository(dsn)`.

### Ajouter une interface

Un module dans `interfaces/` qui reçoit un `ScoutingService` et utilise `presenters` pour la
sortie. CLI et API en sont les deux exemples ; un bot ou un tableau de bord suivrait le même schéma.

### Créer un nouveau domaine

Copier la structure de `fuzzyirrigation` : une base TOML, un module `domain` (mesure d'entrée,
décision), un service qui charge le système et l'évalue, une interface. Le moteur n'est pas
modifié.

## 7.6 Déboguer une base de connaissances

- `fuzzyscout validate` liste les étapes, règles et entrées requises ; toute erreur indique le
  fichier et l'index de la règle fautive.
- `fuzzyscout evaluate … --explain` montre les degrés de chaque entrée dans chaque terme ; une
  règle attendue qui ne se déclenche pas est presque toujours une question de recouvrement des
  termes.
- Un avertissement « Aucune règle n'a conclu » signale un trou de couverture : ajouter une règle de
  couverture à faible poids (voir `technique/attaquant.toml`, règles T12-T13).
- `tests/scouting/test_knowledge.py::test_rule_bases_cover_the_whole_input_space` tire 300
  points aléatoires par poste et échoue sur le premier trou, en affichant les valeurs d'entrée.

## 7.7 Intégration continue

Un flux GitHub Actions (`.github/workflows/ci.yml`) exécute la porte qualité sur Python 3.11, 3.12 et
3.13 à chaque push. Toute contribution doit la laisser verte.
