"""Normalisation and graded comparisons specific to Moroccan identity data.

The key idea for names is the **consonant skeleton**: Arabic → Latin transliteration
variants differ mostly by vowels and doubled consonants (Mohamed / Mohammed /
Muhammad → ``mhmd``), while the first letter and the consonants are stable. Prefixes
such as *El*, *Ben*, *Ait* are dropped before comparison (El Amrani / Lamrani).
"""

from __future__ import annotations

from fuzzyprolog.textsim import jaro_winkler, normalize
from identitylink.domain.record import DateValue, PersonRecord

PARTICLES = frozenset(
    {"el", "al", "ben", "bin", "ibn", "ould", "ait", "bent", "l", "abou", "abu"}
    | {"es", "ez", "ed", "er", "en", "et"}  # article assimilé collé : Essaidi, Ezzahra, Errachidi
)
VOWELS = set("aeiouy")
DIGRAPHS = (("ph", "f"), ("ck", "k"), ("q", "k"), ("sh", "ch"), ("dj", "j"))
NAME_FLOOR = 0.6
GLUED_MIN_LENGTH = 4
"""Minimum length of what remains once a glued particle (Ben…, El…) is removed."""
"""Below this similarity two names are considered unrelated (hard failure)."""


def name_forms(text: str) -> list[str]:
    """Comparable spellings of a name: as written (blanks removed), without particle
    tokens (*El Amrani* → *amrani*) and without a glued particle prefix
    (*Lamrani* → *amrani*, *Benjelloun* → *jelloun*). Longest first."""
    tokens = normalize(text).split()
    if not tokens:
        return []
    forms: list[str] = ["".join(tokens)]
    stripped = "".join(t for t in tokens if t not in PARTICLES)
    if stripped and stripped != forms[0]:
        forms.append(stripped)
    joined = forms[0]
    for particle in sorted(PARTICLES, key=len, reverse=True):
        minimum = GLUED_MIN_LENGTH + (1 if len(particle) == 1 else 0)  # Lotfi stays Lotfi
        if joined.startswith(particle) and len(joined) - len(particle) >= minimum:
            if joined[len(particle) :] not in forms:
                forms.append(joined[len(particle) :])
            break
    return forms


def _skeleton(form: str) -> str:
    for old, new in DIGRAPHS:
        form = form.replace(old, new)
    skeleton: list[str] = []
    previous = ""
    for ch in form:
        doubled = ch == previous
        previous = ch
        if ch in VOWELS or doubled:  # vowels dropped, doubled consonants (mm, ss) reduced
            continue
        skeleton.append(ch)
    return form[0] + "".join(skeleton)


def name_keys(text: str) -> list[str]:
    """Blocking keys (first letter + consonant skeleton) of every form of the name."""
    keys: list[str] = []
    for form in name_forms(text):
        key = _skeleton(form)
        if key not in keys:
            keys.append(key)
    return keys


def name_key(text: str) -> str:
    """Canonical key: the one of the most stripped form (``""`` for an empty name)."""
    forms = name_forms(text)
    return _skeleton(min(forms, key=len)) if forms else ""


def name_similarity(a: str, b: str) -> float:
    """Graded similarity of two names, in ``[0, 1]``.

    Best score over every pair of comparable forms: 1 when a form is shared, else the
    ``max`` of the Jaro-Winkler similarity of the forms and of a skeleton-based score
    (0.92 when skeletons are equal, 0.9 × Jaro-Winkler of the skeletons when both are
    long enough to be meaningful). Returns 0 below :data:`NAME_FLOOR`.
    """
    forms_a, forms_b = name_forms(a), name_forms(b)
    if not forms_a or not forms_b:
        return 0.0
    best = 0.0
    for fa in forms_a:
        for fb in forms_b:
            if fa == fb:
                return 1.0
            ka, kb = _skeleton(fa), _skeleton(fb)
            if ka == kb:
                skeleton_score = 0.92
            elif min(len(ka), len(kb)) >= 4:
                skeleton_score = 0.9 * jaro_winkler(ka, kb)
            else:
                skeleton_score = 0.0  # too short to be meaningful (Nor / Nadia)
            best = max(best, jaro_winkler(fa, fb), skeleton_score)
    return best if best >= NAME_FLOOR else 0.0


def date_similarity(a: DateValue, b: DateValue) -> float:
    """Graded closeness of two recorded birth dates (0 when unknown or incompatible)."""
    if not a.is_known or not b.is_known:
        return 0.0
    if a.is_full and b.is_full:
        assert (
            a.month is not None and a.day is not None and b.month is not None and b.day is not None
        )
        if a == b:
            return 1.0
        same_year, same_month, same_day = a.year == b.year, a.month == b.month, a.day == b.day
        if same_year and same_month and abs(a.day - b.day) <= 3:
            return 0.85  # typo on the day
        if same_year and a.month == b.day and a.day == b.month:
            return 0.75  # day / month swapped
        if same_month and same_day and abs(a.year - b.year) == 1:  # type: ignore[operator]
            return 0.7  # typo on the year (strong signal: same day and month)
        if same_year:
            return 0.4
        return 0.0
    assert a.year is not None and b.year is not None
    if a.year == b.year:
        return 0.7 if (a.is_full or b.is_full) else 0.6
    if abs(a.year - b.year) == 1:
        return 0.3
    return 0.0


def normalize_phone(text: str) -> str:
    """Keep digits, drop the Moroccan country code and the trunk zero: 9 significant digits."""
    digits = "".join(c for c in text if c.isdigit())
    if digits.startswith("00212"):
        digits = digits[5:]
    elif digits.startswith("212") and len(digits) >= 12:
        digits = digits[3:]
    if digits.startswith("0") and len(digits) == 10:
        digits = digits[1:]
    return digits


def phone_similarity(a: str, b: str) -> float:
    na, nb = normalize_phone(a), normalize_phone(b)
    if not na or not nb:
        return 0.0
    if na == nb:
        return 1.0
    if len(na) >= 8 and na[-8:] == nb[-8:]:
        return 0.8
    return 0.0


def blocking_keys(record: PersonRecord) -> set[str]:
    """Keys shared by records that are worth comparing (avoids the n² comparison)."""
    keys: set[str] = set()
    for key in name_keys(record.last_name):
        keys.add(f"nom:{key}")
    forms = name_forms(record.last_name)
    if forms and len(forms[0]) >= 4:
        keys.add(f"nom4:{forms[0][:4]}")
    phone = normalize_phone(record.phone)
    if len(phone) >= 8:
        keys.add(f"tel:{phone[-8:]}")
    if record.birth.is_full:
        keys.add(f"nais:{record.birth}")
    if record.email.strip():
        keys.add(f"mail:{record.email.strip().casefold()}")
    return keys
