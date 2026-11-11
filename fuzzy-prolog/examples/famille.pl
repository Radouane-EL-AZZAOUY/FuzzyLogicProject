% Exemple du cours (« Les éléments fondamentaux du Prolog », p. 73-75) : faits et règles.
%   fuzzyprolog examples/famille.pl -q "grand_parent(X, Y)."

pere(ali, mohamed).
pere(mohamed, youssef).
mere(aicha, ali).
mere(aicha, fatima).
masculin(ali). masculin(mohamed). masculin(youssef).
feminin(aicha). feminin(fatima).

fils(A, B) :- pere(B, A), masculin(A).
fils(A, B) :- mere(B, A), masculin(A).
parent(X, Y) :- pere(X, Y).
parent(X, Y) :- mere(X, Y).
grand_parent(X, Y) :- parent(X, Z), parent(Z, Y).
ancetre(X, Y) :- parent(X, Y).
ancetre(X, Y) :- parent(X, Z), ancetre(Z, Y).
