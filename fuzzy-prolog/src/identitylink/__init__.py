"""identitylink — rapprochement d'identités (détection de doublons) par Prolog flou.

Problème réel : les bases de personnes (étudiants, patients, clients, état civil)
contiennent des doublons dus aux variantes de translittération arabe → latin
(Mohamed / Mohammed / Muhammad, El Amrani / Lamrani), aux dates approximatives et
aux adresses hétérogènes. L'application exprime les règles de rapprochement en
Prolog flou (``fuzzyprolog``) : chaque décision est graduée et prouvée.

Couches : ``domain`` (fiches, normalisation, résultats), ``application`` (dédoublonnage,
évaluation), ``infrastructure`` (CSV, bases de règles), ``interfaces`` (CLI, présentation).
"""

__version__ = "0.1.0"
