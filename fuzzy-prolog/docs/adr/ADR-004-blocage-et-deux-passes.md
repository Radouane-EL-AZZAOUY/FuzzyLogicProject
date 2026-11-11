# ADR-004 — Blocage par clés et résolution en deux passes

**Statut** : accepté — 2026-10-13

## Contexte

Comparer toutes les paires de n fiches coûte O(n²) résolutions ; tracer chaque dérivation pour
l'expliquer multiplie encore le coût. La première version (index élargi à toutes les constantes du
même type, trace systématique) mettait plus de cinq minutes sur 257 fiches.

## Décision

1. Le domaine calcule des **clés de blocage** (squelettes de nom, téléphone, courriel) émises
   comme faits `bloc/2` ; la règle `candidat/2` ne génère que les paires d'un même bloc.
2. L'index par premier argument ne s'élargit qu'aux constantes réellement similaires.
3. Le dédoublonnage fait **deux passes** : requête globale sans trace, puis re-preuve avec trace
   des seules paires retenues.

## Conséquences

- (+) 257 fiches en ≈ 6 s ; les explications restent complètes pour chaque rapprochement.
- (−) Une paire sans clé commune n'est jamais examinée : les clés doivent couvrir les variantes
  attendues (plusieurs squelettes par nom, préfixe de 4 lettres). Le test de rappel sur le jeu
  synthétique garde cette hypothèse sous contrôle.
