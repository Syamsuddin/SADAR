"""Organ B v2 — pemodelan-diri: metrik DETERMINISTIK atas graf workspace (TANPA LLM).

Mengganti _coherence_proxy lama (sekadar hitungan item) dengan ukuran NYATA yang dapat ditambat
ke snapshot() → self-model yang JUJUR. Ini BUKAN metrik spektral riset penuh (SIG/PSI/TIF §8.1) —
itu masih ditunda; v2 menambah ukuran INTEGRASI (konektivitas semantik) di atas v1 graf.

Empat ukuran (semua 0..1, dihitung di KODE):
  - coherence           : rata-rata kemiripan kosinus SEMUA pasangan isi → integrasi semantik global
  - fragmentation       : 1 - (komponen-terhubung-terbesar / n) atas edge caused_by → keterpecahan graf
  - grounding_integrity : fraksi isi yang bersumber input/memori (bukan lamunan LLM) → keberakaran
  - integration (v2)    : rata-rata 'tautan terbaik' tiap isi → menghukum 'pulau' (isi tanpa tetangga mirip)
confidence (turunan) = rata-rata (coherence, grounding_integrity, 1-fragmentation, integration).
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
    integration: float          # v2: konektivitas semantik (tiap isi terhubung ke keseluruhan)
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


def _integration(vecs: list[list[float]]) -> float:
    """v2 — KONEKTIVITAS semantik: rata-rata 'tautan terbaik' tiap isi ke isi lain.
    Beda dari coherence (rata-rata SEMUA pasangan): ini menghukum 'pulau' (isi yang tak punya
    tetangga mirip) — ukuran seberapa workspace menjadi SATU keseluruhan, bukan kepingan terpisah.
    1.0 bila <2 isi (tak ada keterpisahan)."""
    vs = [v for v in vecs if v]
    if len(vs) < 2:
        return 1.0
    per = []
    for i in range(len(vs)):
        best = max((cosine(vs[i], vs[j]) for j in range(len(vs)) if j != i), default=0.0)
        per.append(max(0.0, best))
    return sum(per) / len(per)


def appraise(workspace_items: list[Representation]) -> SelfModel:
    """Hitung self-model dari isi workspace NON-ephemeral (detak jam diabaikan)."""
    live = [r for r in workspace_items if not r.ephemeral]
    vecs = [r.vec for r in live if r.vec]
    coh = round(_coherence(vecs), 3)
    frag = round(_fragmentation(live), 3)
    grd = round(_grounding(live), 3)
    integ = round(_integration(vecs), 3)
    conf = round((coh + grd + (1.0 - frag) + integ) / 4.0, 3)   # v2: integrasi ikut menimbang
    return SelfModel(coherence=coh, fragmentation=frag, grounding_integrity=grd,
                     integration=integ, confidence=conf)
