"""Use case: find duplicate records with the fuzzy Prolog rules.

Two passes keep it fast: the global query ``meme_personne(A, B)`` runs without proof
trace (thousands of derivations), then the best derivation of each retained pair is
re-proved with the trace on, which is what the explanations show.
"""

from __future__ import annotations

import time
from collections.abc import Iterable, Sequence

from fuzzyprolog import (
    Atom,
    Engine,
    Program,
    Settings,
    Solution,
    String,
    Struct,
    Term,
    add_source,
    prelude_program,
)
from fuzzyprolog.textsim import normalize
from fuzzyprolog.tnorms import TNorm
from identitylink.builtins import LINKAGE_BUILTINS, date_term
from identitylink.domain.match import LinkageReport, MatchCandidate, cluster
from identitylink.domain.normalization import blocking_keys
from identitylink.domain.ports import KnowledgeSource
from identitylink.domain.record import PersonRecord

DECISION = "meme_personne"


def record_facts(record: PersonRecord) -> list[Term]:
    """``fiche/6`` and ``bloc/2`` facts describing one record."""
    identifier = Atom(record.identifier)
    facts: list[Term] = [
        Struct(
            "fiche",
            (
                identifier,
                String(record.last_name.strip()),
                String(record.first_name.strip()),
                date_term(record.birth),
                String(normalize(record.city)),
                String(record.phone.strip()),
            ),
        )
    ]
    facts.extend(Struct("bloc", (String(key), identifier)) for key in sorted(blocking_keys(record)))
    return facts


def build_program(records: Iterable[PersonRecord], knowledge: KnowledgeSource) -> Program:
    """Prelude + rules + similarities + one fact set per record."""
    program = Program()
    program.extend(prelude_program())
    add_source(program, knowledge.rules(), "regles.pl")
    add_source(program, knowledge.similarities(), "similarites.pl")
    for record in records:
        for fact in record_facts(record):
            program.add_fact(fact)
    return program


class Deduplicator:
    """Runs the rules on a set of records.

    ``lambda_cut`` and ``tnorm`` override the directives of the rule file *on top of*
    its settings (a ``--tnorm`` option must not silently drop the rules' λ-cut).
    """

    def __init__(
        self,
        knowledge: KnowledgeSource,
        lambda_cut: float | None = None,
        tnorm: TNorm | None = None,
    ) -> None:
        self._knowledge = knowledge
        self._lambda_cut = lambda_cut
        self._tnorm = tnorm

    def settings_for(self, program: Program) -> Settings:
        settings = program.settings
        if self._lambda_cut is not None:
            settings = settings.with_(lambda_cut=self._lambda_cut)
        if self._tnorm is not None:
            settings = settings.with_(tnorm=self._tnorm)
        return settings

    def engine_for(self, records: Sequence[PersonRecord], trace: bool = True) -> Engine:
        program = build_program(records, self._knowledge)
        return Engine(program, self.settings_for(program), builtins=LINKAGE_BUILTINS, trace=trace)

    def run(self, records: Sequence[PersonRecord], threshold: float = 0.7) -> LinkageReport:
        if not 0.0 <= threshold <= 1.0:
            raise ValueError("Le seuil doit être dans [0, 1].")
        started = time.perf_counter()
        engine = self.engine_for(records, trace=False)
        by_id = {r.identifier: r for r in records}
        best: dict[tuple[str, str], float] = {}
        for solution in engine.query(f"{DECISION}(A, B)."):
            pair = (_name(solution.bindings["A"]), _name(solution.bindings["B"]))
            if solution.degree > best.get(pair, 0.0):
                best[pair] = solution.degree
        engine.trace = True
        candidates = tuple(
            sorted(
                (
                    MatchCandidate(by_id[a], by_id[b], degree, _best_proof(engine, a, b, degree))
                    for (a, b), degree in best.items()
                ),
                key=lambda c: (-c.degree, c.pair),
            )
        )
        matched = [c.pair for c in candidates if c.degree >= threshold]
        return LinkageReport(
            threshold=threshold,
            candidates=candidates,
            groups=cluster(records, matched),
            records=len(records),
            seconds=time.perf_counter() - started,
        )


def _best_proof(engine: Engine, a: str, b: str, degree: float) -> Solution:
    """Re-prove one pair with the trace on and keep its strongest derivation."""
    goal = Struct(DECISION, (Atom(a), Atom(b)))
    solutions = list(engine.query((goal,)))
    if not solutions:  # pragma: no cover - pass 1 and pass 2 run the same program
        return Solution({}, degree)
    return max(solutions, key=lambda s: s.degree)


def _name(term: Term) -> str:
    if isinstance(term, Atom):
        return term.name
    if isinstance(term, String):
        return term.value
    raise TypeError(f"identifiant de fiche inattendu : {term!r}")
