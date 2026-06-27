"""Organ B v3 — pemodelan-diri: metrik DETERMINISTIK atas graf workspace (TANPA LLM).

Mengganti _coherence_proxy lama (sekadar hitungan item) dengan ukuran NYATA yang dapat ditambat
ke snapshot() → self-model yang JUJUR. CATATAN JUJUR: ini BUKAN triad riset SIG/PSI/TIF §8.1 (yang
TAK terdefinisi di repo → tak diimplementasi agar tak mengarang); v3 menambah satu metrik SPEKTRAL
STANDAR & terdefinisi (algebraic connectivity / nilai Fiedler) sebagai langkah jujur ke arah spektral.

Lima ukuran (semua 0..1, dihitung di KODE):
  - coherence              : rata-rata kemiripan kosinus SEMUA pasangan isi → integrasi semantik global
  - fragmentation          : 1 - (komponen-terhubung-terbesar / n) atas edge caused_by → keterpecahan
  - grounding_integrity    : fraksi isi bersumber input/memori (bukan lamunan LLM) → keberakaran
  - integration (v2)       : rata-rata 'tautan terbaik' tiap isi → menghukum 'pulau' (semantik)
  - algebraic_connectivity (v3): λ₂ Laplacian graf caused_by (dinormalkan) → integrasi STRUKTURAL spektral
confidence (turunan) = rata-rata (coherence, grounding_integrity, 1-fragmentation, integration).
"""
from __future__ import annotations

from dataclasses import dataclass

from sadar.core.dosir import Representation
from sadar.core.mathx import cosine, eigenvalues_symmetric

# sumber yang 'membumikan' isi pada dunia/memori (vs 'thought' = produksi internal LLM).
_GROUNDED = {"perception", "action_result", "memory", "control"}


@dataclass
class SelfModel:
    coherence: float
    fragmentation: float
    grounding_integrity: float
    integration: float          # v2: konektivitas semantik (tiap isi terhubung ke keseluruhan)
    algebraic_connectivity: float   # v3: spektral (λ₂ Laplacian graf caused_by) — integrasi struktural
    spectral_expansion: float       # v3: kualitas ekspander (gap spektral) — mixing/bebas-silo
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


def _caused_by_adjacency(items: list[Representation]) -> list[list[float]]:
    """Adjacency tak-berarah biner dari edge caused_by INTRA-workspace. Substrat metrik spektral."""
    n = len(items)
    idx = {r.id: i for i, r in enumerate(items)}
    adj = [[0.0] * n for _ in range(n)]
    for r in items:
        for c in r.caused_by:
            if c in idx and idx[c] != idx[r.id]:
                i, j = idx[r.id], idx[c]
                adj[i][j] = adj[j][i] = 1.0
    return adj


def _algebraic_connectivity(items: list[Representation]) -> float:
    """v3 — SPEKTRAL: nilai Fiedler λ₂ (eigenvalue terkecil ke-2) Laplacian graf caused_by, dinormalkan.
    λ₂>0 ⟺ graf terhubung; makin besar = makin terintegrasi. Berbasis STRUKTUR → bebas-embedder.
    Normalisasi λ₂/n ∈ [0,1] (1.0 utk graf lengkap; 0.0 utk terputus). 1.0 bila <2 isi."""
    n = len(items)
    if n < 2:
        return 1.0
    from sadar.core.spectral import laplacian
    eig = eigenvalues_symmetric(laplacian(_caused_by_adjacency(items)))
    lam2 = eig[1] if len(eig) >= 2 else 0.0
    return max(0.0, min(1.0, lam2 / n))


def _spectral_expansion(items: list[Representation]) -> float:
    """v3 — EKSPANDER: gap spektral ternormalkan graf caused_by (lihat spectral.spectral_expansion).
    Tinggi = pikiran terhubung-rapat & bebas-silo (ekspander); 0 = terpecah/bipartit. Ramanujan = optimal."""
    n = len(items)
    if n < 2:
        return 1.0
    from sadar.core.spectral import spectral_expansion
    return spectral_expansion(_caused_by_adjacency(items))


def appraise(workspace_items: list[Representation]) -> SelfModel:
    """Hitung self-model dari isi workspace NON-ephemeral (detak jam diabaikan)."""
    live = [r for r in workspace_items if not r.ephemeral]
    vecs = [r.vec for r in live if r.vec]
    coh = round(_coherence(vecs), 3)
    frag = round(_fragmentation(live), 3)
    grd = round(_grounding(live), 3)
    integ = round(_integration(vecs), 3)
    algc = round(_algebraic_connectivity(live), 3)
    expn = round(_spectral_expansion(live), 3)
    conf = round((coh + grd + (1.0 - frag) + integ) / 4.0, 3)   # v2: integrasi ikut menimbang
    return SelfModel(coherence=coh, fragmentation=frag, grounding_integrity=grd,
                     integration=integ, algebraic_connectivity=algc, spectral_expansion=expn,
                     confidence=conf)
