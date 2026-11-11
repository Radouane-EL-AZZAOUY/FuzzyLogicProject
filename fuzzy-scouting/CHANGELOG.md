# Journal des modifications

Le format suit [Keep a Changelog](https://keepachangelog.com/fr/1.1.0/) et le versionnement
[SemVer](https://semver.org/lang/fr/).

## [Non publié]

### Ajouté

- Système de commande Scout : la vitesse, l'accélération et le tacle sont déduits chacun de trois
  mesures, puis déterminent un niveau de 1 à 6 (108 règles, `knowledge/commande/`). Disponible
  pour un joueur ou pour les joueurs d'un même poste : onglet « Commande Scout », commande
  `fuzzyscout level`, routes `/commande…`. Voir `docs/10-commande-scout.md`.
- `fuzzyengine` : entrées floues (`Interval`, `Category`, `Degrees`, `parse_observation`) et
  chaînage flou des pipelines (`chaining="fuzzy"`), qui transmet la conclusion d'une étape à la
  suivante sans défuzzification.
- Observations d'exemple `observations_commande.csv` (valeurs, intervalles, catégories) et script
  `scripts/generate_command_observations.py`.
- Interface web de scouting servie par `fuzzyscout serve` (`/`) : recherche et classement par
  poste avec contraintes, fiche joueur expliquée (courbes d'appartenance, règles déclenchées),
  comparaison, simulateur « et si… ? », consultation des règles, sélection exportable en CSV.
- Lanceurs `scout.cmd` / `scout.sh` : installation, interface web (ouverture du navigateur),
  tests, porte qualité et démonstration en une commande.
- API : `GET /variables` (variables linguistiques et courbes échantillonnées) et
  `GET /knowledge/{poste}` (règles détaillées d'un poste).

## [0.1.0] — 2026-10-13

### Ajouté

- `fuzzyengine` : moteur d'inférence floue sans dépendance (fonctions d'appartenance, variables
  linguistiques, formules, opérateurs de Zadeh / probabilistes / Łukasiewicz, modificateurs,
  inférence de Mamdani, défuzzification centroïde / bissectrice / moyenne des maxima, pipelines,
  langage de règles bilingue, chargeur TOML avec bibliothèque de variables, explications).
- `fuzzyscout` : application de scouting (5 postes, 9 bases de connaissances, filtres nets,
  classement et évaluation avec trace, dépôt CSV, CLI `fuzzyscout`, API HTTP FastAPI).
- `fuzzyirrigation` : contrôleur flou d'irrigation (base de 13 règles, CLI `fuzzyirrigation`).
- Jeu de données synthétique de 40 joueurs et script de génération reproductible.
- Documentation complète (fondements, architecture, référence du moteur, applications, guide
  développeur, déploiement, qualité, ADR, glossaire), Dockerfile et docker-compose.
- Robustesse aux frontières (suite à revue de code) : rejet des valeurs `NaN`/`inf` dans le CSV,
  le domaine et l'API (422), normalisation de toutes les erreurs d'E/S en erreurs métier, repli
  Windows-1252 pour les CSV Excel, ensembles de sortie vides signalés par le défuzzifieur,
  pipelines mal ordonnés refusés au chargement, API synchrone en pool de threads avec validation
  des bases au démarrage, règle S15 rendue cohérente avec S2/S3.
