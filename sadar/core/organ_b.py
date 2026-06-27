"""Organ B v1 — pemodelan-diri: metrik DETERMINISTIK atas graf workspace (TANPA LLM).

Mengganti _coherence_proxy lama (sekadar hitungan item) dengan ukuran NYATA yang dapat
ditambat ke snapshot() → memperluas self-model yang JUJUR. Ini BUKAN metrik spektral riset
(SIG/PSI/TIF §8.1) — itu masih ditunda; ini v1 graf yang sengaja dilabeli jujur sebagai v1.

Tiga ukuran (semua 0..1, dihitung di KODE):
  - coherence           : rata-rata kemiripan kosinus antar-isi panas → integrasi semantik
  - fragmentation       : 1 - (komponen-terhubung-terbesar / n) atas edge caused_by → keterpecahan
  - grounding_integrity : fraksi isi yang bersumber input/memori (bukan lamunan LLM) → keberakaran
confidence (turunan) = rata-rata (coherence, grounding_integrity, 1-fragmentation).
"""
from __future__ import annotations

from dataclasses import dataclass

from sadar.core.dosir import Representation
from sadar.core.mathx import cosine

# sumber yang 'membumikan' isi pada dunia/memori (vs 'thought' = produksi internal LLM).
_GROUNDED = {"perception", "action_result", "memory", "control"}


@dataclass
class SelfModel:
    coherence: float
    fragmentation: float
    grounding_integrity: float
    confidence: float


def _coherence(vecs: list[list[float]]) -> float:
    if len(vecs) < 2:
        return 1.0
    total, m = 0.0, 0
    for i in range(len(vecs)):
        for j in range(i + 1, len(vecs)):
            total += cosine(vecs[i], vecs[j])
            m += 1
    return max(0.0, min(1.0, total / m)) if m else 1.0


def _fragmentation(items: list[Representation]) -> float:
    n = len(items)
    if n <= 1:
        return 0.0
    ids = {r.id for r in items}
    adj: dict[str, set[str]] = {r.id: set() for r in items}
    for r in items:
        for c in r.caused_by:
            if c in ids:
                adj[r.id].add(c)
                adj[c].add(r.id)
    seen: set[str] = set()
    largest = 0
    for r in items:
        if r.id in seen:
            continue
        stack, comp = [r.id], 0
        while stack:
            x = stack.pop()
            if x in seen:
                continue
            seen.add(x)
            comp += 1
            stack.extend(adj[x] - seen)
        largest = max(largest, comp)
    return max(0.0, min(1.0, 1.0 - largest / n))


def _grounding(items: list[Representation]) -> float:
    if not items:
        return 1.0
    grounded = sum(1 for r in items if r.source in _GROUNDED)
    return grounded / len(items)


def appraise(workspace_items: list[Representation]) -> SelfModel:
    """Hitung self-model dari isi workspace NON-ephemeral (detak jam diabaikan)."""
    live = [r for r in workspace_items if not r.ephemeral]
    coh = round(_coherence([r.vec for r in live if r.vec]), 3)
    frag = round(_fragmentation(live), 3)
    grd = round(_grounding(live), 3)
    conf = round((coh + grd + (1.0 - frag)) / 3.0, 3)
    return SelfModel(coherence=coh, fragmentation=frag, grounding_integrity=grd, confidence=conf)
