"""Util TEORI GRAF SPEKTRAL untuk SADAR — teknik STANDAR & terdefinisi (bukan teori riset spesifik).

Dipakai memperkaya kognisi SADAR di atas graf yang sudah ada (Representation/MemoryItem +
edge caused_by/kemiripan-vektor). Murni Python (pakai mathx; core tetap bebas-numpy).

  - eigenvector_centrality : 'isi mana paling SENTRAL' (eigenvektor dominan adjacency, Perron-Frobenius).
  - fiedler_vector         : eigenvektor λ₂ Laplacian → urutan/bipartisi spektral (deteksi 'dua untai pikiran').
  - similarity_graph       : bangun adjacency berbobot dari kemiripan kosinus antar-vektor.
"""
from __future__ import annotations

from sadar.core.mathx import cosine, eigh_symmetric


def similarity_graph(vecs: list[list[float]], threshold: float = 0.3) -> list[list[float]]:
    """Adjacency simetrik berbobot: edge = cosine(vᵢ,vⱼ) bila ≥ threshold (else 0). Tanpa self-loop."""
    n = len(vecs)
    adj = [[0.0] * n for _ in range(n)]
    for i in range(n):
        for j in range(i + 1, n):
            w = max(0.0, cosine(vecs[i], vecs[j]))
            if w >= threshold:
                adj[i][j] = adj[j][i] = w
    return adj


def eigenvector_centrality(adj: list[list[float]], tol: float = 1e-9) -> list[float]:
    """Sentralitas eigenvektor = eigenvektor eigenvalue TERBESAR matriks adjacency (lewat eigh,
    robust untuk graf bipartit — beda dari power iteration yang berosilasi di sana). Dinormalkan
    [0,1] (hub=1). Graf tanpa edge (λmax≈0) → semua 0 (tak ada sentralitas)."""
    n = len(adj)
    if n == 0:
        return []
    if n == 1:
        return [1.0]
    vals, vecs = eigh_symmetric(adj)
    if abs(vals[-1]) < tol:                        # tak ada edge → λmax≈0 → tak ada sentralitas
        return [0.0] * n
    comp = [abs(vecs[r][-1]) for r in range(n)]    # eigenvektor λmax (kolom terakhir)
    mx = max(comp) or 1.0
    return [round(c / mx, 6) for c in comp]


def fiedler_vector(laplacian: list[list[float]]) -> list[float]:
    """Vektor Fiedler = eigenvektor untuk λ₂ (eigenvalue terkecil ke-2) Laplacian. Tanda komponennya
    membelah graf jadi dua kelompok kohesif (bipartisi spektral); urutannya = tata-letak 1-D graf."""
    n = len(laplacian)
    if n < 2:
        return [0.0] * n
    _, vecs = eigh_symmetric(laplacian)
    return [vecs[r][1] for r in range(n)]          # kolom ke-1 = eigenvektor λ₂


def laplacian(adj: list[list[float]]) -> list[list[float]]:
    """Laplacian kombinatorik L = D − A dari adjacency."""
    n = len(adj)
    lap = [[-adj[i][j] for j in range(n)] for i in range(n)]
    for i in range(n):
        lap[i][i] = sum(adj[i])
    return lap
