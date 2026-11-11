"""Domain layer: person records, normalisation and linkage results (no I/O)."""

from identitylink.domain.match import DuplicateGroup, LinkageReport, MatchCandidate, cluster
from identitylink.domain.normalization import (
    blocking_keys,
    date_similarity,
    name_key,
    name_similarity,
    normalize_phone,
    phone_similarity,
)
from identitylink.domain.record import DateValue, PersonRecord

__all__ = [
    "DateValue",
    "DuplicateGroup",
    "LinkageReport",
    "MatchCandidate",
    "PersonRecord",
    "blocking_keys",
    "cluster",
    "date_similarity",
    "name_key",
    "name_similarity",
    "normalize_phone",
    "phone_similarity",
]
