"""fuzzyscout — aide à la décision pour le scouting de joueurs, fondée sur fuzzyengine.

Couches (dépendances orientées vers l'intérieur uniquement) :

* ``domain``         : entités, objets-valeur, ports (interfaces) et règles métier ;
* ``application``    : cas d'utilisation orchestrant le domaine ;
* ``infrastructure`` : adaptateurs concrets (CSV, TOML, ressources embarquées) ;
* ``interfaces``     : points d'entrée (CLI, API HTTP) et présentation ;
* ``bootstrap``      : racine de composition (câblage des dépendances).
"""

__version__ = "0.1.0"
