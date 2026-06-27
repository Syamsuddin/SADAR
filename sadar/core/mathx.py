"""Util numerik murni — SATU rumah untuk cosine (hapus duplikasi di memory*/organ_b)."""
from __future__ import annotations

import math


def cosine(a: list[float], b: list[float]) -> float:
    """Kemiripan kosinus, tahan beda-panjang (potong ke minimum). 0.0 bila vektor kosong."""
    if not a or not b:
        return 0.0
    n = min(len(a), len(b))
    dot = sum(a[i] * b[i] for i in range(n))
    na = math.sqrt(sum(x * x for x in a[:n]))
    nb = math.sqrt(sum(x * x for x in b[:n]))
    return dot / (na * nb) if na and nb else 0.0
