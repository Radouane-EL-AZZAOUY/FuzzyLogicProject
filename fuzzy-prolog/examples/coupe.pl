% Exemple du cours (« Coupe ou Cut », p. 83) : le nombre de solutions selon la place du « ! ».
%   fuzzyprolog examples/coupe.pl -q "p1(X, Y)." -q "p2(X, Y)." -q "p3(X, Y)." -q "p4(X, Y)."
% Attendu : p1 → 6 solutions, p2 → 1, p3 → 3, p4 → 5.

q(a). q(b). q(c).
r(b, b1). r(c, c1). r(a, a1). r(a, a2). r(a, a3).

p1(X, Y) :- q(X), r(X, Y).
p1(d, d1).

p2(X, Y) :- q(X), r(X, Y), !.
p2(d, d1).

p3(X, Y) :- q(X), !, r(X, Y).
p3(d, d1).

p4(X, Y) :- !, q(X), r(X, Y).
p4(d, d1).
