% Prélude : prédicats de manipulation de listes tels que définis dans le cours
% (« Les éléments fondamentaux du Prolog », p. 77), sous leur nom d'origine.

% Appartenance
app(X, [X|_]).
app(X, [_|L]) :- app(X, L).

% Longueur
long([], 0).
long([_|L], N) :- long(L, M), N is M + 1.

% Intersection (version du cours, sans coupe-choix)
intersection([], _, []).
intersection([X|L1], L2, [X|L3]) :- app(X, L2), intersection(L1, L2, L3).
intersection([_|L1], L2, L3) :- intersection(L1, L2, L3).

% Alias et compléments usuels
member(X, L) :- app(X, L).
length(L, N) :- long(L, N).
append([], L, L).
append([H|T], L, [H|R]) :- append(T, L, R).
reverse(L, R) :- reverse_acc(L, [], R).
reverse_acc([], A, A).
reverse_acc([H|T], A, R) :- reverse_acc(T, [H|A], R).
last([X], X).
last([_|T], X) :- last(T, X).
nth0(0, [X|_], X).
nth0(N, [_|T], X) :- N > 0, M is N - 1, nth0(M, T, X).
