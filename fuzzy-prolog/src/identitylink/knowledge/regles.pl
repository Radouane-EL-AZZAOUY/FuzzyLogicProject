% ==========================================================================
% Règles de rapprochement d'identités (Prolog flou).
%
% Faits fournis par l'application pour chaque fiche :
%   fiche(Id, Nom, Prenom, Naissance, Ville, Telephone)
%       Naissance = date(A, M, J) | annee(A) | inconnue ; Ville normalisée.
%   bloc(Cle, Id)     clés de blocage (squelette du nom, téléphone, courriel)
%
% Prédicats gradués fournis par l'application (identitylink.builtins) :
%   nom_similaire(N1, N2)   similarité tenant compte de la translittération
%   date_proche(D1, D2)     proximité graduée de deux dates de naissance
%   date_connue(D)          vrai si la date n'est pas « inconnue »
%   tel_similaire(T1, T2)   égalité de numéros après normalisation
%
% Degré d'une solution = t-norme (min) des degrés rencontrés ; la ligne de la clause
% de décision apparaît dans la preuve, ce qui rend chaque rapprochement explicable.
% ==========================================================================

:- lambda_cut(0.3).

% Paires candidates : même clé de blocage, chaque paire une seule fois (A @< B) et une
% seule solution par paire (la plus petite clé commune), pour ne pas prouver les règles
% plusieurs fois.
candidat(A, B) :- bloc(K, A), bloc(K, B), A @< B, \+ (bloc(K2, A), bloc(K2, B), K2 @< K).

% Comparaisons élémentaires (graduées)
nom_proche(A, B) :-
    fiche(A, N1, _, _, _, _), fiche(B, N2, _, _, _, _), nom_similaire(N1, N2).
prenom_proche(A, B) :-
    fiche(A, _, P1, _, _, _), fiche(B, _, P2, _, _, _), nom_similaire(P1, P2).
naissance_proche(A, B) :-
    fiche(A, _, _, D1, _, _), fiche(B, _, _, D2, _, _), date_proche(D1, D2).
naissance_incompatible(A, B) :-
    fiche(A, _, _, D1, _, _), fiche(B, _, _, D2, _, _),
    date_connue(D1), date_connue(D2), \+ date_proche(D1, D2).
% Unification par similarité : "casa" = "casablanca" réussit au degré déclaré.
meme_ville(A, B) :-
    fiche(A, _, _, _, V1, _), fiche(B, _, _, _, V2, _), V1 \= "", V1 = V2.
meme_telephone(A, B) :-
    fiche(A, _, _, _, _, T1), fiche(B, _, _, _, _, T2), tel_similaire(T1, T2).

% Règles de décision. Le degré « @ » traduit la confiance de l'expert dans la règle.
% R1 : identité nominale + naissance proche.
meme_personne(A, B) :-
    candidat(A, B), nom_proche(A, B), prenom_proche(A, B), naissance_proche(A, B).
% R2 : identité nominale + même téléphone, sans date contradictoire.
meme_personne(A, B) :-
    candidat(A, B), nom_proche(A, B), prenom_proche(A, B),
    meme_telephone(A, B), \+ naissance_incompatible(A, B) @ 0.9.
% R3 : identité nominale + même ville, sans date contradictoire (indice plus faible).
meme_personne(A, B) :-
    candidat(A, B), nom_proche(A, B), prenom_proche(A, B),
    meme_ville(A, B), \+ naissance_incompatible(A, B) @ 0.7.
