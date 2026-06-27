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


def eigenvalues_symmetric(mat: list[list[float]], iters: int = 100, tol: float = 1e-9) -> list[float]:
    """Eigenvalue matriks SIMETRIK via rotasi Jacobi — MURNI Python (tanpa numpy → core ringan).
    Untuk matriks kecil (graf workspace ≤ puluhan node) cukup akurat & deterministik.
    Kembalikan daftar eigenvalue MENAIK. Dipakai Organ B v3 (algebraic connectivity = λ₂ Laplacian)."""
    n = len(mat)
    if n == 0:
        return []
    if n == 1:
        return [float(mat[0][0])]
    a = [list(map(float, row)) for row in mat]
    for _ in range(iters):
        p, q, mx = 0, 1, 0.0
        for i in range(n):                       # cari elemen off-diagonal terbesar
            for j in range(i + 1, n):
                if abs(a[i][j]) > mx:
                    mx, p, q = abs(a[i][j]), i, j
        if mx < tol:
            break
        if a[p][p] == a[q][q]:
            theta = math.pi / 4
        else:
            theta = 0.5 * math.atan2(2 * a[p][q], a[p][p] - a[q][q])
        c, s = math.cos(theta), math.sin(theta)
        for k in range(n):                       # rotasi kolom p,q
            akp, akq = a[k][p], a[k][q]
            a[k][p], a[k][q] = c * akp + s * akq, -s * akp + c * akq
        for k in range(n):                       # rotasi baris p,q
            apk, aqk = a[p][k], a[q][k]
            a[p][k], a[q][k] = c * apk + s * aqk, -s * apk + c * aqk
    return sorted(a[i][i] for i in range(n))
