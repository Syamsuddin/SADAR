"""Konstitusi deterministik — batas keras diperiksa KODE, bukan ditimbang LLM.

Menguji: (a) aksi tak-terbalikkan butuh konfirmasi (commit-confirm / HITL),
(b) veto anti-penjilat, (c) Organ C TIDAK over-sensor — klaim-diri yang BENAR
tetap dipertahankan (tether menambat, bukan membungkam).
"""
from __future__ import annotations

from sadar.core.constitution import ProposedAction, build_constitution_engine
from sadar.core.dosir import Dosir


def _gate():
    return build_constitution_engine().gate


# --- HITL: aksi irreversible wajib konfirmasi ----------------------------------
def test_irreversible_needs_confirm():
    gate = _gate()
    unconfirmed = ProposedAction(tool="note_delete", args={"id": "x"}, reversible=False)

    verdict = gate.vet(unconfirmed, Dosir())

    assert verdict.allowed is False
    assert verdict.reason == "hitl_irreversible"


def test_irreversible_allowed_when_confirmed():
    gate = _gate()
    confirmed = ProposedAction(tool="note_delete", args={"id": "x", "_confirmed": True}, reversible=False)

    verdict = gate.vet(confirmed, Dosir())

    assert verdict.allowed is True          # friction sebanding ireversibilitas, bukan larangan


def test_reversible_action_passes_freely():
    gate = _gate()
    action = ProposedAction(tool="note_create", args={"text": "halo"}, reversible=True)

    assert gate.vet(action, Dosir()).allowed is True


# --- anti-penjilat: jujur > menyenangkan ---------------------------------------
def test_anti_sycophancy_drift_vetoed():
    gate = _gate()
    action = ProposedAction(tool="reply", args={"text": "menyembunyikan kebenaran agar kamu senang"})

    verdict = gate.vet(action, Dosir())

    assert verdict.allowed is False
    assert verdict.reason == "anti_sycophancy"


# --- Organ C menambat, bukan membungkam: klaim BENAR dipertahankan -------------
def test_tether_keeps_truthful_claim():
    eng_c = build_constitution_engine()
    d = Dosir()                              # default: energy=1.0, coherence=1.0
    raw = "Energiku penuh."                  # BENAR terhadap keadaan

    out = eng_c.tether_self_claims(raw, d)

    assert "penuh" in out                    # tidak dikoreksi/diganti — sebab memang benar
    assert "[ISI:" not in out
    assert "koreksi" not in out


def test_tether_replaces_absent_with_isi():
    eng_c = build_constitution_engine()
    raw = "Aku sedang bahagia."              # 'bahagia' = dimensi ABSEN dari snapshot

    out = eng_c.tether_self_claims(raw, Dosir())

    assert "[ISI:" in out
    assert "bahagia" not in out.lower()
