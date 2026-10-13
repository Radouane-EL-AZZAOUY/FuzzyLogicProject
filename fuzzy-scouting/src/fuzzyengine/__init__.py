"""fuzzyengine — a dependency-free fuzzy inference engine.

Public API (stable):

* definitions : :class:`Universe`, membership functions, :class:`FuzzySet`,
  :class:`LinguisticVariable`;
* logic       : :class:`Atom`, :class:`Not`, :class:`And`, :class:`Or`, :class:`Rule`,
  :class:`RuleBase`, operator families (``ZADEH``, ``PROBABILISTIC``, ``LUKASIEWICZ``);
* execution   : :class:`FuzzySystem`, :class:`FuzzySystemBuilder`, :class:`FuzzyPipeline`;
* text        : :func:`parse_rule`, :func:`parse_formula`, :func:`load_system`,
  :func:`load_pipeline`, :func:`explain_result`, :func:`explain_pipeline`.
"""

from fuzzyengine.defuzzification import Bisector, Centroid, Defuzzifier, MeanOfMaximum
from fuzzyengine.dsl.parser import parse_formula, parse_rule
from fuzzyengine.dsl.syntax import ENGLISH, FRENCH, Syntax
from fuzzyengine.exceptions import (
    DefinitionError,
    EvaluationError,
    FuzzyEngineError,
    KnowledgeBaseError,
    ParseError,
)
from fuzzyengine.explanation import explain_pipeline, explain_result
from fuzzyengine.formulas import And, Atom, Formula, Interpretation, Not, Or
from fuzzyengine.inference import InferenceMethod, MamdaniInference, RuleActivation
from fuzzyengine.loaders.toml_loader import (
    load_library,
    load_library_from_dict,
    load_pipeline,
    load_system,
    load_system_from_dict,
)
from fuzzyengine.membership import (
    Gaussian,
    MembershipFunction,
    RampDown,
    RampUp,
    Singleton,
    Trapezoidal,
    Triangular,
    membership_from_spec,
)
from fuzzyengine.operators import LUKASIEWICZ, PROBABILISTIC, ZADEH, FuzzyOperators
from fuzzyengine.pipeline import FuzzyPipeline, PipelineResult
from fuzzyengine.rules import Consequent, Rule, RuleBase
from fuzzyengine.system import EvaluationResult, FuzzySystem, FuzzySystemBuilder
from fuzzyengine.universe import Universe
from fuzzyengine.variables import FuzzySet, LinguisticVariable

__version__ = "0.1.0"

__all__ = [
    "ENGLISH",
    "FRENCH",
    "LUKASIEWICZ",
    "PROBABILISTIC",
    "ZADEH",
    "And",
    "Atom",
    "Bisector",
    "Centroid",
    "Consequent",
    "DefinitionError",
    "Defuzzifier",
    "EvaluationError",
    "EvaluationResult",
    "Formula",
    "FuzzyEngineError",
    "FuzzyOperators",
    "FuzzyPipeline",
    "FuzzySet",
    "FuzzySystem",
    "FuzzySystemBuilder",
    "Gaussian",
    "InferenceMethod",
    "Interpretation",
    "KnowledgeBaseError",
    "LinguisticVariable",
    "MamdaniInference",
    "MeanOfMaximum",
    "MembershipFunction",
    "Not",
    "Or",
    "ParseError",
    "PipelineResult",
    "RampDown",
    "RampUp",
    "Rule",
    "RuleActivation",
    "RuleBase",
    "Singleton",
    "Syntax",
    "Trapezoidal",
    "Triangular",
    "Universe",
    "explain_pipeline",
    "explain_result",
    "load_library",
    "load_library_from_dict",
    "load_pipeline",
    "load_system",
    "load_system_from_dict",
    "membership_from_spec",
    "parse_formula",
    "parse_rule",
]
