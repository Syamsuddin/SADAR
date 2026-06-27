"""Organ B v2 (Slice 4.2) — metrik INTEGRASI (konektivitas semantik) yang dapat ditambat.

Membuktikan: integrasi tinggi saat isi terhubung, turun saat ada 'pulau'; masuk self-model &
snapshot (dijaga test_introspection); 1.0 untuk isi tunggal.
"""
from __future__ import annotations

from sadar.core.dosir import Representation
from sadar.core.organ_b import _integration, appraise


def _rep(vec):
    return Representation(content="x", source="thought", vec=vec)


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
