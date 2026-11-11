% Prolog flou : degrés de clauses, similarités entre constantes, négation graduée.
%   fuzzyprolog examples/flou.pl -q "doublon(A, B)." --explain
%   fuzzyprolog examples/flou.pl -q "\+ aime(ali, lecture)."
%   fuzzyprolog examples/flou.pl -q "with_degree(passionne(X), D)." --tnorm product

% Relation de similarité (réflexive, symétrique, transitive par fermeture max-min)
"Mohamed" ~ "Mohammed" @ 0.9.
"Mohammed" ~ "Muhammad" @ 0.8.      % d'où "Mohamed" ~ "Muhammad" @ 0.8
casablanca ~ casa @ 0.95.

% Faits (degré 1 implicite) et faits gradués
habite(p1, casablanca).
habite(p2, casa).
habite(p3, rabat).
prenom(p1, "Mohamed").
prenom(p2, "Muhammad").
prenom(p3, "Mohamed").
aime(ali, foot) @ 0.8.
aime(ali, lecture) @ 0.3.

% Règles : l'unification « habite(B, V) » avec V = casablanca réussit sur casa au degré 0.95
meme_ville(A, B) :- habite(A, V), habite(B, V).
meme_prenom(A, B) :- prenom(A, P), prenom(B, P).
doublon(A, B) :- meme_prenom(A, B), meme_ville(A, B), A @< B @ 0.9.
passionne(X) :- aime(X, foot) @ 0.9.

% Seuil de coupure : les dérivations de degré < 0.2 sont abandonnées
:- lambda_cut(0.2).
