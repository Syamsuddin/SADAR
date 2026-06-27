"""Teori graf spektral untuk SADAR (teknik STANDAR) — eigensolver, sentralitas, Fiedler, recall.

Membuktikan: eigh_symmetric benar (eigenvalue+eigenvektor); eigenvector_centrality menyoroti hub;
fiedler_vector membelah dua klaster; recall ber-spektral tetap mengembalikan yang relevan (regresi).
"""
from __future__ import annotations

import math

from sadar.config import AppConfig
from sadar.core.mathx import eigh_symmetric
from sadar.core.ports import MemoryItem
from sadar.core.spectral import (eigenvector_centrality, fiedler_vector, laplacian, similarity_graph)
from sadar.main import build_sadar
from sadar.organs.backend_offline import OfflineBackend


def test_eigh_returns_values_and_vectors():
    # matriks diagonal → eigenvalue = diagonal, eigenvektor = basis standar
    vals, vecs = eigh_symmetric([[3.0, 0.0], [0.0, 1.0]])
    assert abs(vals[0] - 1.0) < 1e-6 and abs(vals[1] - 3.0) < 1e-6
    # eigenvektor λ=1 ≈ (0,1), λ=3 ≈ (1,0) (boleh berbeda tanda)
    assert abs(abs(vecs[1][0]) - 1.0) < 1e-6 and abs(abs(vecs[0][1]) - 1.0) < 1e-6


def test_eigenvector_centrality_highlights_hub():
    # graf bintang: node 0 = pusat terhubung ke 1,2,3 (daun hanya ke pusat)
    n = 4
    adj = [[0.0] * n for _ in range(n)]
    for leaf in (1, 2, 3):
        adj[0][leaf] = adj[leaf][0] = 1.0
    cent = eigenvector_centrality(adj)
    assert cent[0] == max(cent) and cent[0] == 1.0          # pusat paling sentral
    assert all(cent[leaf] < cent[0] for leaf in (1, 2, 3))


def test_no_edges_zero_centrality():
    assert eigenvector_centrality([[0.0, 0.0], [0.0, 0.0]]) == [0.0, 0.0]


def test_fiedler_bipartitions_two_clusters():
    # dua segitiga (0-1-2) dan (3-4-5) dihubungkan satu jembatan 2-3 → Fiedler memisah {0,1,2}|{3,4,5}
    edges = [(0, 1), (1, 2), (0, 2), (3, 4), (4, 5), (3, 5), (2, 3)]
    n = 6
    adj = [[0.0] * n for _ in range(n)]
    for i, j in edges:
        adj[i][j] = adj[j][i] = 1.0
    fv = fiedler_vector(laplacian(adj))
    left = [fv[i] for i in (0, 1, 2)]
    right = [fv[i] for i in (3, 4, 5)]
    # satu kelompok bertanda berlawanan dgn kelompok lain (pembelahan spektral)
    assert (max(left) < min(right)) or (max(right) < min(left))


def test_similarity_graph_thresholds():
    adj = similarity_graph([[1.0, 0.0], [1.0, 0.0], [0.0, 1.0]], threshold=0.5)
    assert adj[0][1] > 0.5 and adj[0][2] == 0.0           # mirip terhubung, ortogonal tidak


def test_spectral_recall_still_returns_relevant(tmp_path):
    """Regresi: re-rank spektral tak boleh menghilangkan item paling relevan."""
    eng = build_sadar(AppConfig(store={"root": str(tmp_path / "m")}, loop={"tick_interval_s": 0.0}),
                      backend=OfflineBackend())
    eng.memory.store.write(MemoryItem(content="paspor ada di laci atas meja kerja"))
    eng.memory.store.write(MemoryItem(content="jadwal rapat tim hari selasa"))
    eng.memory.store.write(MemoryItem(content="resep kopi susu gula aren"))
    hits = eng.memory.recall("di mana paspor", k=3)
    assert any("paspor" in h.content for h in hits)
