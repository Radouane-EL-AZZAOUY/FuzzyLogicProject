"""Build programs from source text or files."""

from __future__ import annotations

from collections.abc import Iterable
from importlib import resources
from pathlib import Path

from fuzzyprolog.exceptions import FuzzyPrologError, ProgramError
from fuzzyprolog.parser import flatten_conjunction, parse_program_items
from fuzzyprolog.program import Clause, Program
from fuzzyprolog.terms import Struct, Term, render

PRELUDE_RESOURCE = "prelude.pl"


def add_source(program: Program, text: str, source: str = "<texte>") -> Program:
    """Parse ``text`` and add its clauses, similarities and directives to ``program``."""
    for item in parse_program_items(text):
        term = item.term
        try:
            if isinstance(term, Struct) and term.functor == ":-" and term.arity == 1:
                program.apply_directive(term.args[0])
            elif isinstance(term, Struct) and term.functor == ":-" and term.arity == 2:
                head, body = term.args
                program.add_clause(Clause(head, flatten_conjunction(body), item.degree, item.line))
            elif isinstance(term, Struct) and term.functor == "~" and term.arity == 2:
                program.add_similarity(term.args[0], term.args[1], item.degree)
            else:
                program.add_clause(Clause(term, (), item.degree, item.line))
        except ProgramError as exc:
            raise ProgramError(f"{source}, ligne {item.line} : {exc}") from exc
    return program


def program_from_text(text: str, prelude: bool = True, source: str = "<texte>") -> Program:
    program = Program()
    if prelude:
        program.extend(prelude_program())
    return add_source(program, text, source)


def load_program(paths: Iterable[str | Path], prelude: bool = True) -> Program:
    program = Program()
    if prelude:
        program.extend(prelude_program())
    for path in paths:
        file_path = Path(path)
        try:
            text = file_path.read_text(encoding="utf-8")
        except FileNotFoundError as exc:
            raise ProgramError(f"Fichier introuvable : {file_path}") from exc
        except (OSError, UnicodeDecodeError) as exc:
            raise ProgramError(f"Impossible de lire {file_path} : {exc}") from exc
        try:
            add_source(program, text, str(file_path))
        except FuzzyPrologError as exc:
            raise ProgramError(f"{file_path} : {exc}") from exc
    return program


_PRELUDE: Program | None = None


def prelude_program() -> Program:
    """The course's list predicates, parsed once."""
    global _PRELUDE
    if _PRELUDE is None:
        text = resources.files("fuzzyprolog").joinpath(PRELUDE_RESOURCE).read_text(encoding="utf-8")
        _PRELUDE = add_source(Program(), text, PRELUDE_RESOURCE)
    return _PRELUDE


def facts_program(facts: Iterable[Term], degree: float = 1.0) -> Program:
    program = Program()
    for fact in facts:
        if not isinstance(fact, Struct):
            raise ProgramError(f"Fait invalide : {render(fact)}")
        program.add_fact(fact, degree)
    return program
