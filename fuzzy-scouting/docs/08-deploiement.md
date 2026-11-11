# 8. Déploiement et exploitation

## 8.1 Interface en ligne de commande

```
fuzzyscout [--players CSV] [--knowledge-dir DIR] [--log-level LEVEL] <commande> [options]
```

| Commande | Options | Description |
|---|---|---|
| `positions` | — | Liste les postes évaluables |
| `rank` | `--position CODE` (requis), `--top N`, `--max-age`, `--max-value` (M€), `--min-minutes`, `--nationality`, `--natural-only`, `--explain`, `--json` | Classe les joueurs du CSV pour un poste |
| `evaluate` | `--position CODE`, `--player ID` **ou** `--attr nom=valeur` (répétable) + `--name`, `--explain`, `--json` | Évalue un joueur du CSV ou un candidat ad hoc |
| `validate` | — | Charge et valide toutes les bases de connaissances |
| `serve` | `--host`, `--port`, `--reload` | Démarre l'interface web et l'API HTTP (extra `[api]`) |

Codes de retour : `0` succès ; `1` erreur métier ou de connaissances (message sur stderr) ; `2`
erreur d'usage (argparse). La sortie est forcée en UTF-8 (sûr sous Windows).

```
fuzzyirrigation [--knowledge TOML] decide --humidite-sol X --temperature X --humidite-air X [--pluie-prevue X] [--explain] [--json]
fuzzyirrigation batch mesures.csv [--json]
```

## 8.2 API HTTP

Démarrage : `fuzzyscout serve` ou
`uvicorn fuzzyscout.interfaces.api.app:create_app --factory --host 0.0.0.0 --port 8000`.
Documentation interactive : `/docs` (Swagger UI), `/redoc`, schéma `/openapi.json`.
La racine `/` sert l'interface web (fichiers statiques de `fuzzyscout/interfaces/web/`, exposés
sous `/ui/`) ; elle n'utilise que les routes ci-dessous.

| Méthode | Route | Corps | Réponse |
|---|---|---|---|
| GET | `/health` | — | `{"status": "ok", "version": "…"}` |
| GET | `/positions` | — | liste des postes |
| GET | `/players`, `/players/{id}` | — | joueurs du référentiel (404 si inconnu) |
| GET | `/knowledge` | — | résumé validé des bases (étapes, règles, entrées requises) |
| GET | `/knowledge/{poste}` | — | règles complètes d'un poste, étape par étape (texte, description, poids ; 404 si inconnu) |
| GET | `/variables` | — | variables linguistiques : univers, unité, termes et courbe d'appartenance échantillonnée |
| POST | `/evaluations` | `{position, player_id, trace?}` | évaluation (404 joueur/poste inconnu, 422 statistiques manquantes) |
| POST | `/evaluations/ad-hoc` | `{position, attributes{…}, name?, trace?}` | évaluation d'un candidat transitoire |
| POST | `/rankings` | `{position, limit?, max_age?, max_market_value?, min_minutes?, natural_position_only?, nationality?, trace?}` | classement + exclus |

Exemple :

```bash
curl -s -X POST http://127.0.0.1:8000/rankings \
  -H "Content-Type: application/json" \
  -d '{"position": "attaquant", "limit": 3, "max_age": 26, "min_minutes": 900}'
```

```json
{
  "poste": {"code": "attaquant", "libelle": "Attaquant de pointe", "...": "..."},
  "filtres": ["âge ≤ 26", "minutes ≥ 900"],
  "candidats": 40, "classes": 3,
  "classement": [
    {"rang": 1, "joueur": {"id": "P040", "nom": "Walid Hajji", "...": "..."},
     "aptitude": 83.2, "aptitude_label": "excellente",
     "scores": {"technique": 81.6, "physique": 59.8, "profil": 87.6, "aptitude": 83.2},
     "labels": {"technique": "excellente", "...": "..."}, "avertissements": []}
  ],
  "exclus": [{"id": "P001", "nom": "Jonas Tazi", "raison": "statistiques manquantes : buts_p90, …"}]
}
```

Avec `"trace": true`, chaque évaluation contient `etapes[]` : entrées, degrés d'appartenance,
règles déclenchées (identifiant, force, texte, description, degré de chaque atome), sorties.

Gestion des erreurs : les erreurs sont converties en JSON `{"detail": "…"}` avec le code HTTP
approprié — 404 (joueur ou poste inconnu), 422 (statistiques manquantes, nom vide, `NaN`/`inf`
dans le corps, valeur hors contraintes pydantic), 500 (fichier de joueurs ou base de
connaissances invalide côté serveur, avec le diagnostic).

Au démarrage, l'application **valide toutes les bases et charge le référentiel** (`warm_up`) :
un déploiement cassé échoue immédiatement plutôt qu'à la première requête, et les caches sont
remplis avant tout accès concurrent. Les handlers sont synchrones et exécutés dans le pool de
threads de FastAPI : l'inférence (CPU) ne bloque jamais la boucle d'événements.

## 8.3 Configuration

| Variable d'environnement | Rôle | Défaut |
|---|---|---|
| `FUZZYSCOUT_PLAYERS_CSV` | fichier des joueurs | jeu d'exemple embarqué |
| `FUZZYSCOUT_KNOWLEDGE_DIR` | répertoire des bases (doit contenir `variables.toml`, `positions.toml` et les sous-dossiers) | bases embarquées |
| `FUZZYSCOUT_LOG_LEVEL` | `DEBUG`, `INFO`, `WARNING`, `ERROR` | `INFO` |

Les options `--players` et `--knowledge-dir` de la CLI priment sur l'environnement. Un fichier
`.env.example` documente ces variables.

Pour exploiter des bases personnalisées, copier `src/fuzzyscout/knowledge/` vers un répertoire
versionné à part, le modifier, puis pointer `FUZZYSCOUT_KNOWLEDGE_DIR` dessus : l'application
reste identique, seule la connaissance change. Les pipelines sont mis en cache au premier usage ;
après modification des fichiers, redémarrer le processus (ou appeler
`TomlPipelineProvider.clear()` dans une intégration).

## 8.4 Docker

```bash
docker build -f docker/Dockerfile -t fuzzy-scouting:0.1.0 .
docker run --rm -p 8000:8000 fuzzy-scouting:0.1.0
# ou
docker compose -f docker/docker-compose.yml up --build
```

L'image (multi-étapes, `python:3.13-slim`, utilisateur non privilégié, `HEALTHCHECK` sur
`/health`) n'embarque que le paquet et ses dépendances d'API. Pour vos données, montez un volume
et renseignez `FUZZYSCOUT_PLAYERS_CSV` / `FUZZYSCOUT_KNOWLEDGE_DIR` (voir `docker-compose.yml`).

## 8.5 Journalisation et observabilité

- `logging` standard, format `horodatage niveau module: message` ; niveau via
  `FUZZYSCOUT_LOG_LEVEL` ou `--log-level`.
- En `DEBUG`, la CLI journalise la pile des erreurs métier ; l'API s'appuie sur les journaux
  d'uvicorn (accès) et sur les mêmes journaux applicatifs.
- `/health` pour les sondes ; `/knowledge` pour vérifier à chaud que les bases chargées sont celles
  attendues (nombre de règles par étape).

## 8.6 Performances et capacité

| Mesure (Python 3.13, portable, pur Python) | Valeur |
|---|---|
| Évaluation complète d'un joueur pour un poste (4 étapes, ~55 règles, centroïde à 501 points) | ≈ 4 ms |
| Classement des 40 joueurs d'exemple sur les 5 postes | ≈ 0,6 s |
| Extrapolation : 1 000 joueurs × 1 poste | ≈ 5 s |

Leviers : réduire `resolution` dans `[system]` (201 points suffisent en pratique), paralléliser la
boucle de `RankPlayers` par lots de joueurs, ou mettre en cache les classements par
(poste, filtres) côté API. L'API est sans état : plusieurs réplicas derrière un équilibreur sont
possibles sans coordination.

## 8.7 Sécurité

- L'API n'implémente ni authentification ni limitation de débit : la déployer derrière une
  passerelle (reverse proxy avec TLS, jeton ou SSO, quotas), jamais exposée directement.
- Les entrées sont validées (pydantic côté API, argparse côté CLI) ; les valeurs numériques hors
  univers sont bornées, les NaN refusés.
- Les fichiers TOML sont lus avec `tomllib` (pas d'exécution de code) ; les CSV sont parsés avec le
  module standard `csv`.
- Les données de joueurs sont des données personnelles : appliquer la réglementation applicable
  (minimisation, droits d'accès) sur les CSV que vous branchez.

## 8.8 Mise à jour et versionnement

- Version du paquet dans `pyproject.toml` et `__version__` ; `CHANGELOG.md` tenu à jour.
- Les bases de connaissances devraient être versionnées avec le code (un changement de seuil est
  un changement de comportement) et accompagnées d'un passage de `fuzzyscout validate` et de la
  suite de tests.
