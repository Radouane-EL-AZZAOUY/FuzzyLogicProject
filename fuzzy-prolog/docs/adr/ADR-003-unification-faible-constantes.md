# ADR-003 — Unification faible limitée aux constantes, fermée transitivement

**Statut** : accepté — 2026-10-13

## Contexte

Bousi~Prolog autorise la similarité entre constantes *et* entre foncteurs. Les relations déclarées
peuvent être laissées telles quelles ou fermées (réflexivité, symétrie, transitivité max-min).

## Décision

- Seules les constantes symboliques (atomes, chaînes) sont similaires — les nombres se
  comparent par valeur et une déclaration `1 ~ 2` est refusée ; les foncteurs et arités doivent
  coïncider, comme dans l'algorithme de la page 56.
- La relation est fermée par max-min (Floyd-Warshall) au premier usage ; `:- transitive(false).`
  désactive la fermeture.
- L'index par premier argument s'élargit aux constantes similaires (`related`), jamais à toutes.

## Conséquences

- (+) Les règles restent lisibles : la similarité ne change que la comparaison de données.
- (+) `"Mohamed" ~ "Muhammad"` est déduit de deux déclarations ; les alias de villes se déclarent
  en étoile autour d'un nom canonique.
- (−) La fermeture est en O(k³) sur les k constantes déclarées : adaptée à des centaines de
  déclarations, pas à des dictionnaires de millions d'entrées (qui relèvent d'un prédéfini).
