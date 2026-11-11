% Exemple du cours (« Le raisonnement en Prolog », p. 78-80) : R1 … R11 et l'arbre de recherche.
%   fuzzyprolog examples/humeur.pl -q "est_de_bonne_humeur(X)." --explain
% La preuve affichée suit exactement l'arbre de la page 80 : R1 échoue (pas de soleil en
% juillet), R2 réussit pour aicha via R10 et R11.

est_de_bonne_humeur(X) :- a_de_l_argent(X), est_en_vacances(X), il_y_a_du_soleil.      % R1
est_de_bonne_humeur(X) :- reussit_dans_le_travail(X), reussit_dans_sa_famille(X).      % R2
a_de_l_argent(ali).                                                                   % R3
a_de_l_argent(aicha).                                                                 % R4
est_en_vacances(ali) :- on_est_en(aout).                                              % R5
est_en_vacances(aicha) :- on_est_en(juillet).                                         % R6
on_est_en(juillet).                                                                   % R7
il_y_a_du_soleil :- on_est_en(aout).                                                  % R8
reussit_dans_le_travail(ali).                                                         % R9
reussit_dans_le_travail(aicha).                                                       % R10
reussit_dans_sa_famille(aicha).                                                       % R11
