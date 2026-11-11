"""Programs taken from the course slides, reused across the engine tests."""

from __future__ import annotations

import pytest

from fuzzyprolog import Engine, Program, program_from_text

# p. 73-75 : faits, règles et questions
FAMILLE = """
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
"""

# p. 78-80 : le raisonnement en Prolog (R1 … R11) et son arbre de recherche
HUMEUR = """
est_de_bonne_humeur(X) :- a_de_l_argent(X), est_en_vacances(X), il_y_a_du_soleil.
est_de_bonne_humeur(X) :- reussit_dans_le_travail(X), reussit_dans_sa_famille(X).
a_de_l_argent(ali).
a_de_l_argent(aicha).
est_en_vacances(ali) :- on_est_en(aout).
est_en_vacances(aicha) :- on_est_en(juillet).
on_est_en(juillet).
il_y_a_du_soleil :- on_est_en(aout).
reussit_dans_le_travail(ali).
reussit_dans_le_travail(aicha).
reussit_dans_sa_famille(aicha).
"""

# p. 83 : coupe-choix, quatre variantes de p/2
COUPE = """
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
"""

# p. 81 : négation par l'échec ; p. 84 : récursivité
NEGATION_ET_RECURSION = """
sportif(ali). sportif(sam).
petit(sam).
fort(X) :- sportif(X), not(petit(X)).
factoriel(1, 1).
factoriel(N, R) :- N > 1, N1 is N - 1, factoriel(N1, F1), R is N * F1.
"""

# Programme flou : similarités, degrés de clauses
FLOU = """
"Mohamed" ~ "Mohammed" @ 0.9.
"Mohammed" ~ "Muhammad" @ 0.8.
casablanca ~ casa @ 0.95.
habite(p1, casablanca).
habite(p2, casa).
habite(p3, rabat).
prenom(p1, "Mohamed").
prenom(p2, "Muhammad").
prenom(p3, "Mohamed").
meme_ville(A, B) :- habite(A, V), habite(B, V).
meme_prenom(A, B) :- prenom(A, P), prenom(B, P).
doublon(A, B) :- meme_prenom(A, B), meme_ville(A, B), A @< B @ 0.9.
aime(ali, foot) @ 0.8.
aime(ali, lecture) @ 0.3.
passionne(X) :- aime(X, foot) @ 0.9.
"""


def engine_for(text: str, **kwargs: object) -> Engine:
    return Engine(program_from_text(text), **kwargs)  # type: ignore[arg-type]


def solutions(engine: Engine, query: str) -> list[str]:
    return [str(s) for s in engine.query(query)]


@pytest.fixture
def famille() -> Engine:
    return engine_for(FAMILLE)


@pytest.fixture
def humeur() -> Engine:
    return engine_for(HUMEUR)


@pytest.fixture
def coupe() -> Engine:
    return engine_for(COUPE)


@pytest.fixture
def flou() -> Engine:
    return engine_for(FLOU)


@pytest.fixture
def flou_program() -> Program:
    return program_from_text(FLOU)
