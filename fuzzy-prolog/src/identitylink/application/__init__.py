"""Application layer: use cases built on the domain and the fuzzy Prolog engine."""

from identitylink.application.deduplicate import Deduplicator, build_program
from identitylink.application.evaluate import Metrics, evaluate, sweep, truth_pairs

__all__ = ["Deduplicator", "Metrics", "build_program", "evaluate", "sweep", "truth_pairs"]
