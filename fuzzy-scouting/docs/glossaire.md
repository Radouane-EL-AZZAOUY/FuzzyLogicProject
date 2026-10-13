# Glossaire

| Terme | Définition |
|---|---|
| **Activation (force, α)** | Degré de vérité de l'antécédent d'une règle, multiplié par le poids de la règle. |
| **Agrégation** | Combinaison (t-conorme, `max` par défaut) des conclusions de toutes les règles portant sur une même sortie. |
| **Antécédent** | Partie `SI …` d'une règle : une formule bien formée floue. |
| **Atome** | Proposition élémentaire `variable EST terme`. |
| **Centroïde** | Méthode de défuzzification : centre de gravité de l'ensemble flou de sortie. |
| **Chaînage avant** | Stratégie d'inférence partant des faits pour produire toutes les conclusions (par opposition au chaînage arrière de Prolog). |
| **Clause de Horn** | Règle `Tête :- C1, …, Cn` ; une règle floue en est la version graduée. |
| **Conséquent** | Partie `ALORS variable EST terme` d'une règle. |
| **Défuzzification** | Passage d'un ensemble flou de sortie à une valeur numérique. |
| **Degré d'appartenance** | Valeur `μ_A(x) ∈ [0, 1]` mesurant à quel point `x` appartient à l'ensemble flou `A`. |
| **Ensemble flou** | Ensemble caractérisé par une fonction d'appartenance à valeurs dans `[0, 1]`. |
| **Extension conservative** | La logique floue redonne la logique classique quand les degrés sont restreints à `{0, 1}`. |
| **Fonction d'appartenance** | Fonction `μ : D → [0, 1]` définissant un ensemble flou (triangle, trapèze, rampe, gaussienne…). |
| **Fuzzification** | Calcul des degrés d'appartenance d'une mesure à chaque terme de sa variable ; construit l'interprétation. |
| **Implication (floue)** | Opérateur combinant la force d'une règle et la fonction d'appartenance de son conséquent (`min` : écrêtage ; produit : mise à l'échelle). |
| **Interprétation (δ)** | Assignation d'une valeur de vérité à chaque atome ; `{□, ■}` dans le cours, `[0, 1]` ici. |
| **Modificateur linguistique** | Opérateur sur un degré : `très` (`μ²`), `assez` (`√μ`), `extrêmement` (`μ³`). |
| **Modus ponens généralisé** | Règle d'inférence : de `G → H` et `G'` vrai au degré α, conclure `H'` (H affaibli à α). |
| **p90** | Statistique normalisée « par 90 minutes jouées ». |
| **Pipeline** | Enchaînement de systèmes flous ; les sorties d'une étape alimentent les suivantes. |
| **Poste** | Rôle sur le terrain (gardien, défenseur central, milieu central, ailier, attaquant) ; chaque poste a sa chaîne de bases de connaissances. |
| **Règle de couverture** | Règle à antécédent simple et faible poids garantissant qu'une conclusion existe en tout point de l'espace d'entrée. |
| **Système formel** | Alphabet + langage + axiomes + règles de déduction (cours, p. 33) ; un `FuzzySystem` en est une instance. |
| **t-norme / t-conorme** | Généralisations de `∧` et `∨` à `[0, 1]` (min/max, produit/somme probabiliste, Łukasiewicz). |
| **Terme linguistique** | Étiquette d'un ensemble flou d'une variable (`lente`, `moyenne`, `rapide`). |
| **Univers de discours** | Intervalle de valeurs possibles d'une variable (le domaine `D` du cours). |
| **Variable linguistique** | Grandeur mesurable associée à un univers et à des termes. |
| **xG** | *Expected goals* : nombre de buts attendus compte tenu de la qualité des tirs. |
