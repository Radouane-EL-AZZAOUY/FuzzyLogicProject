# Glossaire

| Terme | Définition |
|---|---|
| **Atome** | Constante symbolique (`ali`) ; aussi, formule atomique `P(t₁,…,tₙ)`. |
| **Blocage** | Technique de rapprochement : ne comparer que les fiches partageant une clé (squelette de nom, téléphone) pour éviter la comparaison de toutes les paires. |
| **Clause de Horn** | `Tête :- C₁, …, Cₙ` : la tête est vraie si chaque `Cᵢ` l'est (cours, p. 75). |
| **Coupe-choix (`!`)** | Prédicat qui interdit de revenir sur les choix faits dans la clause courante (p. 82). |
| **Degré de vérité** | Valeur dans `]0, 1]` attachée à une clause, à une unification ou à une solution. |
| **Dérivation / preuve** | Suite d'inférences menant d'une requête aux faits ; affichée par `--explain`. |
| **Fermeture max-min** | Transitivité floue : `R(a,c) ≥ min(R(a,b), R(b,c))` pour tout `b`. |
| **λ-coupure** | Abandon des dérivations dont le degré est inférieur à λ. |
| **Négation par l'échec** | `\+ G` réussit si `G` échoue (monde clos, p. 81) ; graduée : `1 − sup`. |
| **Occurs check** | Refus d'unifier `X` avec un terme contenant `X` (p. 56). |
| **Rapprochement d'identités** (*record linkage*) | Détection des enregistrements décrivant la même entité réelle. |
| **Résolution SLD** | Stratégie de Prolog : linéaire, sélection du but le plus à gauche, clauses définies. |
| **Renommage (θ)** | Substitution donnant des noms de variables frais à une clause avant son usage (p. 60). |
| **Similarité (relation de)** | Relation floue réflexive, symétrique, transitive sur les constantes, déclarée par `a ~ b @ d`. |
| **Squelette consonantique** | Clé d'un nom : première lettre + consonnes, sans voyelles ni doublons (`Mohamed → mmhmd`). |
| **Substitution (σ)** | Ensemble de couples variable → terme ; `A σ` est l'application à `A` (p. 54). |
| **t-norme** | Généralisation de la conjonction à `[0,1]` : `min`, produit, Łukasiewicz. |
| **Translittération** | Transcription d'un nom arabe en alphabet latin, non normalisée (d'où les variantes). |
| **Unification faible** | Unification où deux constantes distinctes mais similaires s'unifient au degré de leur similarité (Sessa). |
| **Unificateur le plus général** | Substitution rendant deux termes identiques, dont toute autre est une instance (p. 55). |
