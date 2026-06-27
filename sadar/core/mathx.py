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


def eigh_symmetric(mat: list[list[float]], iters: int = 100, tol: float = 1e-9):
    """Eigenvalue + EIGENVEKTOR matriks SIMETRIK via rotasi Jacobi — MURNI Python (tanpa numpy).
    Untuk matriks kecil (graf workspace ≤ puluhan node) cukup akurat & deterministik. Kembalikan
    (eigenvalues MENAIK, eigenvectors) — eigenvectors[r][i] = komponen-r dari eigenvector ke-i (kolom).
    Dipakai util graf spektral (Fiedler/clustering) & Organ B (λ₂ Laplacian)."""
    n = len(mat)
    if n == 0:
        return [], []
    if n == 1:
        return [float(mat[0][0])], [[1.0]]
    a = [list(map(float, row)) for row in mat]
    v = [[1.0 if i == j else 0.0 for j in range(n)] for i in range(n)]   # akumulasi eigenvektor
    for _ in range(iters):
        p, q, mx = 0, 1, 0.0
        for i in range(n):                       # cari elemen off-diagonal terbesar
            for j in range(i + 1, n):
                if abs(a[i][j]) > mx:
                    mx, p, q = abs(a[i][j]), i, j
        if mx < tol:
            break
        theta = (math.pi / 4 if a[p][p] == a[q][q]
                 else 0.5 * math.atan2(2 * a[p][q], a[p][p] - a[q][q]))
        c, s = math.cos(theta), math.sin(theta)
        for k in range(n):                       # rotasi kolom p,q pada A
            akp, akq = a[k][p], a[k][q]
            a[k][p], a[k][q] = c * akp + s * akq, -s * akp + c * akq
        for k in range(n):                       # rotasi baris p,q pada A
            apk, aqk = a[p][k], a[q][k]
            a[p][k], a[q][k] = c * apk + s * aqk, -s * apk + c * aqk
        for k in range(n):                       # putar pula V (kumpulan eigenvektor)
            vkp, vkq = v[k][p], v[k][q]
            v[k][p], v[k][q] = c * vkp + s * vkq, -s * vkp + c * vkq
    order = sorted(range(n), key=lambda i: a[i][i])
    vals = [a[i][i] for i in order]
    vecs = [[v[r][i] for i in order] for r in range(n)]
    return vals, vecs


def eigenvalues_symmetric(mat: list[list[float]], iters: int = 100, tol: float = 1e-9) -> list[float]:
    """Eigenvalue MENAIK matriks simetrik (wrapper eigh_symmetric)."""
    return eigh_symmetric(mat, iters, tol)[0]
