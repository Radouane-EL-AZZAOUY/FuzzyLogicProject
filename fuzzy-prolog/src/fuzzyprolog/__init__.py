"""fuzzyprolog — a fuzzy logic-programming engine (Prolog with similarity-based
unification and graded SLD resolution), written to mirror the course
*Programmation logique* step by step.

Public API:

* terms            : :class:`Var`, :class:`Atom`, :class:`Number`, :class:`String`,
  :class:`Struct`, :func:`make_list`, :func:`list_items`, :func:`render`;
* logic            : :class:`Substitution`, :func:`unify`, :class:`SimilarityRelation`,
  :class:`Clause`, :class:`Program`, :class:`Settings`, t-norms;
* text             : :func:`parse_query`, :func:`parse_term`, :func:`program_from_text`,
  :func:`load_program`;
* execution        : :class:`Engine`, :class:`Solution`, :class:`ProofStep`,
  :func:`register` (custom built-ins).
"""

from fuzzyprolog.builtins import BUILTINS, Builtin, register
from fuzzyprolog.engine import Engine
from fuzzyprolog.exceptions import (
    DepthLimitError,
    ExecutionError,
    FuzzyPrologError,
    InstantiationError,
    ParseError,
    ProgramError,
)
from fuzzyprolog.loader import add_source, load_program, prelude_program, program_from_text
from fuzzyprolog.parser import parse_query, parse_term
from fuzzyprolog.program import Clause, Program, Settings
from fuzzyprolog.similarity import SimilarityRelation
from fuzzyprolog.solution import ProofStep, Solution
from fuzzyprolog.substitution import EMPTY, Substitution
from fuzzyprolog.terms import (
    EMPTY_LIST,
    Atom,
    Number,
    String,
    Struct,
    Term,
    Var,
    list_items,
    make_list,
    render,
)
from fuzzyprolog.tnorms import TNORMS, TNorm, tnorm_from_name
from fuzzyprolog.unification import Unifier, unify

__version__ = "0.1.0"

__all__ = [
    "BUILTINS",
    "EMPTY",
    "EMPTY_LIST",
    "TNORMS",
    "Atom",
    "Builtin",
    "Clause",
    "DepthLimitError",
    "Engine",
    "ExecutionError",
    "FuzzyPrologError",
    "InstantiationError",
    "Number",
    "ParseError",
    "Program",
    "ProgramError",
    "ProofStep",
    "Settings",
    "SimilarityRelation",
    "Solution",
    "String",
    "Struct",
    "Substitution",
    "TNorm",
    "Term",
    "Unifier",
    "Var",
    "add_source",
    "list_items",
    "load_program",
    "make_list",
    "parse_query",
    "parse_term",
    "prelude_program",
    "program_from_text",
    "register",
    "render",
    "tnorm_from_name",
    "unify",
]
