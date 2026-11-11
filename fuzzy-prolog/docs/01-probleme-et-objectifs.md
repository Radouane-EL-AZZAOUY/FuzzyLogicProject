# 1. Problème et objectifs

## 1.1 Le problème réel : les doublons d'identité

Toute base de personnes construite à partir de saisies humaines — inscriptions d'étudiants,
dossiers patients, fichiers clients, registres administratifs — finit par contenir plusieurs
fiches pour une même personne. Au Maroc (et plus largement dans le monde arabe), une cause
dominante est la **translittération** des noms arabes en alphabet latin : *Mohamed*, *Mohammed*,
*Muhammad*, *M'hamed* désignent le même prénom ; *El Amrani*, *Lamrani*, *El-Amrani* le même nom.
S'y ajoutent les fautes de frappe, les dates de naissance saisies à l'année près ou avec jour et
mois inversés, les villes sous plusieurs noms (*Casablanca*, *Casa*, *Dar El Beida*), les numéros de
téléphone formatés différemment.

Les conséquences sont concrètes : statistiques faussées, courriers en double, dossiers médicaux
fragmentés, fraudes à l'inscription non détectées. Le *record linkage* (rapprochement
d'enregistrements) est un domaine établi (Fellegi-Sunter, 1969), mais ses modèles probabilistes
sont opaques pour l'agent qui doit décider de fusionner deux fiches.

## 1.2 Pourquoi la programmation logique floue

Les praticiens formulent naturellement des **règles** : « deux fiches désignent la même personne
si les noms se ressemblent, les prénoms se ressemblent et la date de naissance est proche ; ou si,
à défaut de date, elles partagent le téléphone sans date contradictoire ». Ces règles sont :

- **symboliques** : elles raisonnent sur des entités (fiches, villes) et des relations ;
- **graduées** : « se ressemblent », « proche » sont des notions à degrés ;
- **explicables** : un rapprochement doit pouvoir être justifié à un opérateur (et, pour des
  données personnelles, à un responsable de traitement).

Prolog (cours, p. 72-84) offre le cadre symbolique ; la logique floue offre les degrés. Le **Prolog
flou** réunit les deux : unification par similarité, résolution graduée, règles pondérées, et une
preuve pour chaque réponse. Un contrôleur flou numérique (Mamdani) ne saurait pas manipuler les
fiches, les variables et le chaînage de règles ; un Prolog classique dirait « non » dès que
`mohamed ≠ mohammed`.

## 1.3 Objectifs

| # | Objectif | Vérification |
|---|---|---|
| O1 | Un moteur de Prolog flou complet : termes, unification faible, résolution SLD graduée, coupe-choix, négation par l'échec, arithmétique, listes, prédéfinis gradués, λ-coupure, trace de preuve | `tests/engine` (exemples du cours rejoués) |
| O2 | Un langage lisible : syntaxe Prolog standard + `@ degré` + `a ~ b` | chapitre 4 |
| O3 | Une application réelle : dédoublonnage de fiches avec variantes de translittération, dates approximatives, villes alias | `identitylink dedupe` |
| O4 | Des décisions **expliquées** (la dérivation complète) et **mesurées** (précision, rappel, F1 contre une vérité terrain) | `--explain`, `identitylink evaluate` |
| O5 | Alignement explicite avec le cours (unification p. 56, résolution p. 60, Prolog p. 72-84) | chapitre 2 et tests |
| O6 | Qualité pré-production : architecture en couches, typage strict, 93 % de couverture, CLI, Docker | chapitres 3, 6, 7 |

## 1.4 Périmètre

**Inclus** : moteur et REPL `fuzzyprolog` ; application `identitylink` (CLI, règles, similarités,
générateur de données synthétiques avec vérité terrain, évaluation) ; documentation ; tests.

**Exclus** : interface web, connecteurs de bases de données (le format CSV est documenté et un
adaptateur suffit), fusion automatique des fiches (l'application *propose* des groupes, la décision
finale reste humaine), apprentissage automatique des poids des règles.

## 1.5 Hypothèses

- Les fiches ont au moins un nom ou un prénom ; les autres champs peuvent manquer.
- Les données d'exemple sont **synthétiques** (noms et personnes fictifs) ; les règles et seuils
  sont des points de départ à calibrer sur des données réelles avec `identitylink evaluate`.
- Les données de personnes réelles relèvent de la loi 09-08 (CNDP) : le système n'exporte rien,
  travaille sur des fichiers locaux et journalise ses décisions sous forme de preuves.
