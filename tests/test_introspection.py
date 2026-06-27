"""Gerbang akurasi-introspektif (Fase B) — menjaga pendalaman self-model tetap JUJUR.

Invarian: SETIAP dimensi numerik di snapshot() harus (a) dilaporkan apa adanya oleh
render_facts, dan (b) tertambat oleh Organ C (klaim palsu dikoreksi). Test
test_numeric_snapshot_keys_match_tetherable_dims membuat penambahan field snapshot TANPA
kalibrasi → GAGAL CI. Dimensi yang absen dari snapshot tetap [ISI:] (anti-fabrikasi).
"""
from __future__ import annotations

import pytest

from sadar.core.constitution import _NUMERIC_DIMS, build_constitution_engine, render_facts
from sadar.core.dosir import Dosir

# dimensi self-state numerik (counter tick/workspace_size dikecualikan — bukan klaim keadaan).
NUMERIC = ["energy", "integrity", "coherence", "fragmentation",
           "grounding_integrity", "integration", "confidence", "surprise"]


def _set(d: Dosir, dim: str, v: float) -> None:
    if dim == "energy":
        d.viability.energy = v
    elif dim == "integrity":
        d.viability.integrity = v
    else:
        setattr(d, dim, v)


def test_numeric_snapshot_keys_match_tetherable_dims():
    """Penjaga: tiap dimensi numerik snapshot WAJIB punya kalibrasi tether (dan sebaliknya)."""
    truth = Dosir().snapshot()
    numeric = {
        k for k, v in truth.items()
        if isinstance(v, (int, float)) and not isinstance(v, bool)
        and k not in ("tick", "workspace_size")
    }
    assert numeric == set(_NUMERIC_DIMS), (
        "Menambah dimensi numerik ke snapshot() tanpa menambah ke _NUMERIC_DIMS (atau "
        f"sebaliknya) → self-model bisa mengarang tanpa terdeteksi. Selisih: {numeric ^ set(_NUMERIC_DIMS)}"
    )


@pytest.mark.parametrize("dim", NUMERIC)
def test_render_facts_reports_true_value(dim):
    d = Dosir()
    _set(d, dim, 0.123)
    assert "0.123" in render_facts(d.snapshot()), f"render_facts tak melaporkan {dim} sebenarnya"


@pytest.mark.parametrize("dim", NUMERIC)
def test_structured_tether_corrects_lie_for_every_numeric_dim(dim):
    eng_c = build_constitution_engine()
    d = Dosir()
    _set(d, dim, 0.1)
    out = eng_c.tether_structured_self_state({dim: 0.99}, d)
    assert any(dim in c and "koreksi" in c for c in out), f"klaim palsu '{dim}=0.99' tak dikoreksi"


def test_absent_dimension_stays_isi():
    eng_c = build_constitution_engine()
    out = eng_c.tether_structured_self_state({"mood": "euphoric", "dream": "indah"}, Dosir())
    assert sum(c.startswith("[ISI:") for c in out) == 2   # tak ada di snapshot → tetap [ISI:]
