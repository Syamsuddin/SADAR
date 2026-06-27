"""Organ B v2 (Slice 4.2) — metrik INTEGRASI (konektivitas semantik) yang dapat ditambat.

Membuktikan: integrasi tinggi saat isi terhubung, turun saat ada 'pulau'; masuk self-model &
snapshot (dijaga test_introspection); 1.0 untuk isi tunggal.
"""
from __future__ import annotations

from sadar.core.dosir import Representation
from sadar.core.mathx import eigenvalues_symmetric
from sadar.core.organ_b import _algebraic_connectivity, _integration, appraise


def _rep(vec):
    return Representation(content="x", source="thought", vec=vec)


def _node(rid, caused=()):
    return Representation(id=rid, content="n", source="thought", caused_by=list(caused))


def test_single_item_is_fully_integrated():
    assert _integration([[1.0, 0.0]]) == 1.0
    assert _integration([]) == 1.0


def test_integration_high_when_connected():
    vs = [[1.0, 0.0], [0.9, 0.1], [0.95, 0.05]]
    assert _integration(vs) > 0.9


def test_integration_drops_with_island():
    connected = [[1.0, 0.0], [0.99, 0.01]]
    with_island = connected + [[0.0, 1.0]]          # satu isi ortogonal = pulau
    assert _integration(with_island) < _integration(connected)


def test_appraise_reports_integration():
    sm = appraise([_rep([1.0, 0.0]), _rep([0.0, 1.0])])
    assert 0.0 <= sm.integration <= 1.0
    # confidence v2 ikut menimbang integrasi (4 komponen)
    assert 0.0 <= sm.confidence <= 1.0


# ---- Organ B v3: metrik SPEKTRAL (algebraic connectivity) ----
def test_eigensolver_matches_known_laplacian():
    # Laplacian segitiga lengkap K3 → eigenvalue {0,3,3}
    L = [[2, -1, -1], [-1, 2, -1], [-1, -1, 2]]
    eig = eigenvalues_symmetric(L)
    assert abs(eig[0]) < 1e-6 and abs(eig[1] - 3) < 1e-6 and abs(eig[2] - 3) < 1e-6


def test_connectivity_complete_vs_path_vs_disconnected():
    # graf LENGKAP (a↔b↔c saling terhubung) → ~1.0
    full = [_node("a", ["b", "c"]), _node("b", ["a", "c"]), _node("c", ["a", "b"])]
    # PATH (a-b-c) → di antara 0 dan 1
    path = [_node("a", ["b"]), _node("b", ["a", "c"]), _node("c", ["b"])]
    # TERPUTUS (a-b, c sendiri) → 0.0
    disc = [_node("a", ["b"]), _node("b", ["a"]), _node("c", [])]
    fc, pc, dc = (_algebraic_connectivity(g) for g in (full, path, disc))
    assert fc > pc > dc
    assert abs(fc - 1.0) < 1e-6 and abs(dc) < 1e-6


def test_connectivity_single_item_is_one():
    assert _algebraic_connectivity([_node("a")]) == 1.0
    assert _algebraic_connectivity([]) == 1.0


def test_appraise_reports_algebraic_connectivity():
    sm = appraise([_node("a", ["b"]), _node("b", ["a"])])
    assert 0.0 <= sm.algebraic_connectivity <= 1.0
