"""Shared helpers for UN/ECE regulation cross-references.

A "UN R number" is the canonical form ``UN R<digits>[<uppercase-letter>]``
(e.g. ``UN R94``, ``UN R13H``). ECE record ids encode the same number
(``ece-r94`` -> ``UN R94``, ``ece-r13-h`` -> ``UN R13H``).
"""
from __future__ import annotations

import re

_CANON_RE = re.compile(r"^UN R(\d+)([A-Z]?)$")
_ECE_ID_RE = re.compile(r"^ece-r(\d+)(?:-([a-z]))?$")
# A variant suffix (e.g. R13H) is always ADJACENT to the number — no whitespace
# between them. Allowing whitespace would absorb the first letter of a following
# word as a bogus suffix (e.g. Portuguese "UN R34 e UN R94" -> "UN R34E").
_CITATION_RE = re.compile(
    r"\b(?:UN\s+R|ECE\s+R|UNECE\s+R)\s*(\d+)([A-Za-z]?)\b"
    r"|\b(?:UN|ECE|UNECE)\s+Regulation\s+No\.?\s*(\d+)([A-Za-z]?)\b",
    re.IGNORECASE,
)


def normalize_un(value: str) -> str | None:
    """Return the canonical ``UN R<N>[<SUFFIX>]`` form, or None if invalid.

    Accepts inputs like ``"un r94"``, ``"R94"``, ``"UN R13H"``.
    A trailing letter suffix is only valid when it is uppercase in the original
    input (e.g. ``"UN R13H"`` is valid; ``"UN R94x"`` is not).
    """
    if not isinstance(value, str):
        return None
    text = value.strip()
    # Normalize prefix to uppercase but preserve the case of any trailing letter
    # so that _CANON_RE's [A-Z]? can distinguish a legitimate suffix (uppercase)
    # from a stray character (lowercase).
    text_upper = text.upper()
    if not text_upper.startswith("UN R"):
        text_upper = "UN R" + text_upper.lstrip("R").lstrip()
    # Rebuild: use the uppercased prefix but keep suffix from original casing.
    # Strategy: match digits at the end and check the trailing alpha char.
    m = _CANON_RE.match(text_upper)
    if not m:
        return None
    number, suffix_upper = m.group(1), m.group(2)
    if int(number) < 1:
        return None
    # If there is a suffix, verify it was uppercase in the original stripped input.
    if suffix_upper:
        # Find the suffix character in the original (stripped) input — it must
        # appear as uppercase at the end of the token.
        if not text.strip().endswith(suffix_upper):
            return None
    return f"UN R{int(number)}{suffix_upper}"


def ece_id_to_un(reg_id: str) -> str | None:
    m = _ECE_ID_RE.match(reg_id or "")
    if not m:
        return None
    number, suffix = m.group(1), (m.group(2) or "")
    return normalize_un(f"UN R{number}{suffix.upper()}")


def scan_grounded_un(body: str) -> list[str]:
    found: set[str] = set()
    for m in _CITATION_RE.finditer(body or ""):
        number = m.group(1) or m.group(3)
        suffix = (m.group(2) or m.group(4) or "")
        canon = normalize_un(f"UN R{number}{suffix.upper()}")
        if canon:
            found.add(canon)
    return sorted(found, key=lambda s: (int(re.search(r"\d+", s).group()), s))
