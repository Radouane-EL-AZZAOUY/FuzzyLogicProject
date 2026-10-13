# ADR-002 — Inférence de Mamdani en chaînage avant

**Statut** : accepté — 2026-10-13

## Contexte

Deux grandes familles d'inférence floue existent : Mamdani (conséquents flous, défuzzification
géométrique) et Takagi-Sugeno (conséquents numériques, moyenne pondérée). Par ailleurs, le cours
présente la résolution et le chaînage arrière de Prolog.

## Décision

1. Implémenter la méthode de **Mamdani** (implication `min`, agrégation `max`, centroïde par
   défaut ; implication produit et autres agrégations configurables).
2. Évaluer les règles en **chaînage avant** : toutes les règles sont activées en parallèle à
   partir des faits fuzzifiés ; pas de but, pas d'unification, pas de backtracking.
3. Abstraire la méthode derrière `InferenceMethod` afin qu'une inférence de Sugeno puisse être
   ajoutée sans toucher au reste du moteur.

## Justification

- Mamdani s'exprime entièrement en termes linguistiques (`aptitude EST excellente`), ce que
  comprend et peut rédiger un recruteur ; Sugeno exige des coefficients numériques.
- Le problème est « tous les faits connus → toutes les conclusions », cas d'usage naturel du
  chaînage avant ; le résultat est déterministe et la trace complète (explicabilité).
- La résolution/unification du cours n'apporterait rien ici : chaque atome est un prédicat
  d'arité 1 déjà instancié par la mesure.

## Conséquences

- (+) Explications lisibles, règles rédigeables par un expert métier.
- (−) Le centroïde peut produire de petites non-monotonies locales (plateaux des termes) ; les
  tests tolèrent 1 point sur 100 et vérifient la tendance globale.
- (−) Pas de raisonnement récursif (règles dont la conclusion alimente une autre règle du même
  système) ; ce besoin est couvert par les pipelines (ADR-005).
