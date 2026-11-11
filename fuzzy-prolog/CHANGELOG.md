# Journal des modifications

## [0.1.0] — 2026-10-13

### Ajouté

- `fuzzyprolog` : moteur de programmation logique floue en Python pur — termes, substitutions,
  unification faible par relation de similarité (fermeture max-min), clauses graduées (`@`),
  résolution SLD graduée (t-normes min / produit / Łukasiewicz), λ-coupure, coupe-choix, négation
  par l'échec graduée, `call/N`, `findall/3`, arithmétique, ordre standard, prédicats de listes du
  cours (prélude), prédéfinis gradués extensibles, trace de preuve, parseur Prolog à précédence
  d'opérateurs, CLI et REPL.
- `identitylink` : rapprochement d'identités (doublons avec variantes de translittération, dates
  approximatives, alias de villes, téléphones) — normalisation (formes de noms, squelette
  consonantique), règles Prolog flou, blocage, dédoublonnage en deux passes, groupes (union-find),
  évaluation précision / rappel / F1, générateur de données synthétiques avec vérité terrain,
  CLI (`dedupe`, `evaluate`, `query`, `generate`).
- Revue de code indépendante intégrée : échappement des atomes quotés, variables anonymes
  non aliasables, négation calculée sans λ-coupure (élagage sain), `findall/3` copiant son
  patron, erreurs Python converties (but non appelable, dépassement arithmétique, CSV
  illisible), index sur les deux premiers arguments, une seule solution `candidat/2` par paire,
  options CLI appliquées par-dessus les directives des règles, similarités limitées aux
  variantes de graphie, squelette consonantique corrigé.
- Exemples exécutables du cours (`examples/`), documentation (fondements, architecture,
  référence du langage, application, guide développeur, qualité, ADR, glossaire), CI, Dockerfile.
