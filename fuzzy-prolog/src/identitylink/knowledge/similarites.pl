% Relation de similarité entre constantes (villes normalisées en minuscules sans accents).
% Réflexive et symétrique par construction, transitive par fermeture max-min.
%
% Règle d'usage : « ~ » exprime des VARIANTES DE GRAPHIE ou des noms historiques d'une même
% ville (degré ≥ 0.8), jamais une proximité géographique : deux villes voisines ne sont pas
% « la même ville » et un tel lien ferait rapprocher des homonymes. Une proximité géographique
% relèverait d'un prédéfini gradué dédié (ville_proche/3), utilisé explicitement par une règle.
"casablanca" ~ "casa" @ 0.95.
"casablanca" ~ "dar el beida" @ 0.9.
"mohammedia" ~ "fedala" @ 0.85.
"fes" ~ "fez" @ 0.95.
"marrakech" ~ "marrakesh" @ 0.95.
"tanger" ~ "tangier" @ 0.95.
"tanger" ~ "tanja" @ 0.9.
"meknes" ~ "meknas" @ 0.9.
"oujda" ~ "oujda angad" @ 0.9.
"el jadida" ~ "mazagan" @ 0.85.
"essaouira" ~ "mogador" @ 0.85.
"laayoune" ~ "el aaiun" @ 0.9.
