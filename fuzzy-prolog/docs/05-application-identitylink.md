# 5. Application `identitylink` : rapprochement d'identités

## 5.1 Données d'entrée

Fichier CSV (`,` ou `;`, UTF-8 avec ou sans BOM, ou Windows-1252) :

| Colonne | Obligatoire | Format |
|---|---|---|
| `id` | oui | identifiant unique |
| `nom`, `prenom` | oui (au moins un non vide) | texte libre |
| `date_naissance` | non | `AAAA-MM-JJ`, `JJ/MM/AAAA`, `AAAA` (année seule) ou vide |
| `ville` | non | texte libre (normalisé en minuscules sans accents) |
| `telephone` | non | tout format ; `+212`, `00212`, `0` initial et séparateurs sont neutralisés |
| `email`, `source` | non | informatifs (`email` sert de clé de blocage) |

Vérité terrain (pour `evaluate`) : CSV `id,personne` associant chaque fiche à la personne réelle.

## 5.2 Normalisation (domaine)

**Formes d'un nom** (`name_forms`) : la graphie normalisée sans blancs, la graphie sans
particules (*el, al, ben, bin, ibn, ould, ait, bent, l, abou, abu* et les articles assimilés
*es, ez, ed, er, en, et*), et la graphie sans particule *collée* (*Lamrani* → *amrani*,
*Benjelloun* → *jelloun*, *Essaidi* → *saidi*, si le reste a ≥ 4 lettres).

**Squelette consonantique** (`name_key`) : première lettre + consonnes, voyelles supprimées,
consonnes doublées (consécutives) réduites, digrammes unifiés (*ph→f, q→k, ck→k, sh→ch, dj→j*) :
*Mohamed / Mohammed / Muhammad → `mmhmd`*. C'est la clé de blocage principale et le cœur de la
similarité : deux noms de même squelette valent 0,92.

**Similarité de noms** (`name_similarity`) : maximum, sur toutes les paires de formes, de
Jaro-Winkler(formes) et du score de squelettes (0,92 si égaux, 0,9 × Jaro-Winkler des
squelettes si tous deux ont ≥ 4 caractères). Formes identiques ⇒ 1. Sous 0,6 ⇒ 0 (échec).

**Dates** (`date_similarity`) : identiques 1 ; jour ± 3 (même mois/année) 0,85 ; jour et mois
inversés 0,75 ; année ± 1 (même jour/mois) 0,7 ; même année seulement 0,4 ; année seule vs date
complète de même année 0,7 ; deux années seules égales 0,6 ; sinon 0 ; inconnue ⇒ 0.

**Téléphones** : 9 chiffres significatifs ; égaux 1 ; mêmes 8 derniers chiffres 0,8.

**Clés de blocage** : `nom:<squelette>` pour chaque forme du nom, `nom4:<4 premières lettres>`,
`tel:<8 derniers chiffres>`, `mail:<courriel>`, `nais:<date complète>`.

## 5.3 Base de connaissances (`knowledge/regles.pl`)

Faits générés pour chaque fiche : `fiche(Id, Nom, Prenom, Naissance, Ville, Tel)` avec
`Naissance ∈ {date(A,M,J), annee(A), inconnue}` et `bloc(Cle, Id)`.

```prolog
:- lambda_cut(0.3).

candidat(A, B) :- bloc(K, A), bloc(K, B), A @< B, \+ (bloc(K2, A), bloc(K2, B), K2 @< K).

nom_proche(A, B)      :- fiche(A, N1, _, _, _, _), fiche(B, N2, _, _, _, _), nom_similaire(N1, N2).
prenom_proche(A, B)   :- fiche(A, _, P1, _, _, _), fiche(B, _, P2, _, _, _), nom_similaire(P1, P2).
naissance_proche(A, B):- fiche(A, _, _, D1, _, _), fiche(B, _, _, D2, _, _), date_proche(D1, D2).
naissance_incompatible(A, B) :- fiche(A, _, _, D1, _, _), fiche(B, _, _, D2, _, _),
                                date_connue(D1), date_connue(D2), \+ date_proche(D1, D2).
meme_ville(A, B)      :- fiche(A, _, _, _, V1, _), fiche(B, _, _, _, V2, _), V1 \= "", V1 = V2.
meme_telephone(A, B)  :- fiche(A, _, _, _, _, T1), fiche(B, _, _, _, _, T2), tel_similaire(T1, T2).

% R1 : identité nominale + naissance proche.
meme_personne(A, B) :- candidat(A, B), nom_proche(A, B), prenom_proche(A, B), naissance_proche(A, B).
% R2 : identité nominale + même téléphone, sans date contradictoire.
meme_personne(A, B) :- candidat(A, B), nom_proche(A, B), prenom_proche(A, B),
                       meme_telephone(A, B), \+ naissance_incompatible(A, B) @ 0.9.
% R3 : identité nominale + même ville, sans date contradictoire (indice plus faible).
meme_personne(A, B) :- candidat(A, B), nom_proche(A, B), prenom_proche(A, B),
                       meme_ville(A, B), \+ naissance_incompatible(A, B) @ 0.7.
```

Trois mécanismes flous s'y combinent :

1. les **prédéfinis gradués** fournis par l'application (`nom_similaire/2`, `date_proche/2`,
   `tel_similaire/2`) ;
2. l'**unification par similarité** dans `meme_ville/2` : `V1 = V2` réussit sur
   `"casa"`/`"casablanca"` au degré déclaré dans `similarites.pl` ;
3. les **degrés de règles** (`@ 0.9`, `@ 0.7`) qui traduisent la confiance de l'expert ;
4. la **négation graduée** `\+ naissance_incompatible` : une date « à moitié compatible »
   (même année seulement) pénalise sans interdire.

Le degré final d'une paire est le `min` de tout cela ; s'il existe plusieurs dérivations
(plusieurs règles ou plusieurs clés de blocage), la meilleure est retenue.

## 5.4 Lire un rapport

```
$ identitylink dedupe --threshold 0.7
Rapprochement d'identités — 257 fiches, seuil 0.70
Paires candidates : 113 | rapprochements ≥ seuil : 109 | groupes : 75 | 4.6 s

 degré  A      B      fiche A                                    fiche B                                    règle
  1.00  p0038  p0158  Yassine Boukhari (2003-07-28, Oujda)       Yassine Boukhary (2003-07-28, Oujda)       l.42
  0.95  p0118  p0137  Sihm El Alaoui (2000-03-17, Mogador)       Siham Alaoui (2000-03-17, Essaouira)       l.42
  ...
Groupes de doublons probables :
  - p0023 Yassine Bokhari | p0038 Yassine Boukhari | p0158 Yassine Boukhary
```

`--explain` ajoute, sous chaque paire, la dérivation complète (règle utilisée, faits, degrés
des prédéfinis, similarités). `--all` montre aussi les paires sous le seuil ; `--json` produit la
même information structurée.

## 5.5 Évaluation sur le jeu synthétique

Jeu embarqué : 257 fiches issues de 162 personnes fictives (150 + 12 homonymes de contrôle),
113 paires vraies. Perturbations : variantes de translittération (tables de 30 prénoms et
30 noms), fautes de frappe, dates à l'année près / jour-mois inversés / ± 2 jours / année ± 1 /
inconnues, alias de villes, téléphones reformatés ou absents, courriels absents.

```
$ identitylink evaluate
 seuil    VP    FP    FN  précision   rappel      F1
  0.50   109     2     4      0.982    0.965   0.973
  0.70   109     0     4      1.000    0.965   0.982
  0.80    85     0    28      1.000    0.752   0.859
  0.90    63     0    50      1.000    0.558   0.716
```

Au seuil 0,7 (point de fonctionnement recommandé), les homonymes (même nom et prénom, autre
date et autre ville) ne produisent **aucun faux positif** grâce à `naissance_incompatible` ; les
deux faux positifs qui apparaissent sous 0,6 sont des homonymes partageant une ville. Les faux
négatifs restants (quatre) sont des fiches qui n'ont **ni date, ni téléphone, ni ville** en commun
avec leur doublon, ou dont la date n'est compatible qu'à l'année près : sans indice discriminant, s'abstenir est le comportement voulu — ces fiches sont
exactement celles qu'un opérateur doit compléter.

Clés de blocage et préfixes assimilés (*Es-saidi*, *Oud/Ould Said*) : voir §5.2 ; ils ont fait
passer le rappel de 0,87 à 0,97 sans faux positif (ADR-004). La négation `\+` étant calculée
sans λ-coupure (chapitre 4), les degrés des règles R2 et R3 reflètent fidèlement la compatibilité
des dates : c'est ce qui fait chuter le rappel aux seuils ≥ 0,9.

## 5.6 Interroger directement la base

```
$ identitylink query "meme_personne(p0118, X)." --explain
$ identitylink query "fiche(X, N, _, annee(1990), _, _)."
$ identitylink query "with_degree(meme_personne(p0023, B), D)."
```

La base construite est un programme Prolog flou ordinaire : toute requête du chapitre 4 est
possible, ce qui sert au diagnostic d'une règle ou d'une fiche.

## 5.7 Limites connues des heuristiques

- Deux noms de même squelette consonantique valent 0,92 même s'ils diffèrent par les
  voyelles (*Salim / Selma*, *Said / Saad*) : c'est le prix des variantes de translittération.
  Les règles exigent donc toujours un second indice (date, téléphone, ville) et
  `naissance_incompatible` bloque les homonymes datés.
- La suppression d'une particule collée (*L-*, *Ben-*, *Al-*) peut rapprocher des noms distincts
  (*Alaoui / Laoui*) ; elle exige au moins 4 lettres restantes (5 pour *L-*).
- La relation `~` ne doit contenir que des variantes de graphie (≥ 0,85) ; une proximité
  géographique y créerait des faux positifs via la règle R3.

## 5.8 Calibrer sur ses données

1. Constituer un échantillon annoté (`id,personne`) de quelques centaines de fiches.
2. `identitylink evaluate fiches.csv --truth verite.csv --errors` pour voir les faux positifs et
   négatifs.
3. Ajuster `similarites.pl` (alias locaux), les seuils de `normalization.py` ou les règles
   (`--rules mes_regles.pl`), puis réévaluer. Les degrés `@` des règles et le seuil `--threshold`
   règlent le compromis précision / rappel.
