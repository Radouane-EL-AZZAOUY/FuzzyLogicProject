"""Generic text similarity used by graded built-ins (domain-independent)."""

from __future__ import annotations

import unicodedata


def normalize(text: str) -> str:
    """Lower-case, strip accents, keep letters/digits, collapse blanks."""
    decomposed = unicodedata.normalize("NFKD", text.casefold())
    stripped = "".join(c for c in decomposed if not unicodedata.combining(c))
    cleaned = "".join(c if c.isalnum() else " " for c in stripped)
    return " ".join(cleaned.split())


def jaro(a: str, b: str) -> float:
    if a == b:
        return 1.0
    if not a or not b:
        return 0.0
    window = max(len(a), len(b)) // 2 - 1
    window = max(window, 0)
    a_flags = [False] * len(a)
    b_flags = [False] * len(b)
    matches = 0
    for i, ca in enumerate(a):
        lo, hi = max(0, i - window), min(len(b), i + window + 1)
        for j in range(lo, hi):
            if not b_flags[j] and b[j] == ca:
                a_flags[i] = b_flags[j] = True
                matches += 1
                break
    if matches == 0:
        return 0.0
    transpositions = 0
    k = 0
    for i, flagged in enumerate(a_flags):
        if not flagged:
            continue
        while not b_flags[k]:
            k += 1
        if a[i] != b[k]:
            transpositions += 1
        k += 1
    transpositions //= 2
    return (matches / len(a) + matches / len(b) + (matches - transpositions) / matches) / 3.0


def jaro_winkler(a: str, b: str, prefix_scale: float = 0.1, max_prefix: int = 4) -> float:
    """Jaro-Winkler similarity in ``[0, 1]`` (rewards common prefixes)."""
    base = jaro(a, b)
    prefix = 0
    for ca, cb in zip(a, b, strict=False):
        if ca != cb or prefix >= max_prefix:
            break
        prefix += 1
    return base + prefix * prefix_scale * (1.0 - base)


def text_similarity(a: str, b: str) -> float:
    """Jaro-Winkler on normalised texts."""
    return jaro_winkler(normalize(a), normalize(b))
