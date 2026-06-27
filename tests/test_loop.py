"""Lingkaran kognitif — tick() berputar & lingkaran aksi-persepsi menutup.

Menguji: (a) loop berdetak stabil tanpa efek samping (SilentBackend),
(b) pesan pengguna → deliberasi → aksi → HASIL kembali jadi persepsi,
(c) TIDAK fire-and-forget: setiap hasil-aksi membawa jejak kausal (caused_by).
"""
from __future__ import annotations

from sadar.organs.backend_offline import OfflineBackend
from tests.mocks import SilentBackend, build_test_sadar


# --- loop berdetak stabil -------------------------------------------------------
def test_loop_spins(tmp_path):
    eng = build_test_sadar(tmp_path, SilentBackend())

    eng.run(max_ticks=5)

    assert eng.d.tick_count == 5
    assert eng.d.mode in ("autonomous", "non_autonomous")


# --- lingkaran aksi-persepsi menutup -------------------------------------------
def test_action_perception_loop(tmp_path):
    eng = build_test_sadar(tmp_path, OfflineBackend())
    eng.perceiver.push("ingatkan aku rapat jam 9")     # masuk via INDRA, bukan langsung ke LLM

    eng.tick()

    # aksi terjadi → catatan tertulis ke memori persisten
    assert len(eng.memory.store.list()) >= 1
    # HASIL aksi kembali masuk kesadaran sebagai persepsi-hasil
    results = [r for r in eng.d.workspace.items if r.source == "action_result"]
    assert results, "hasil aksi tidak kembali ke workspace (lingkaran tidak menutup)"


# --- anti fire-and-forget: hasil-aksi tahu pemicunya ---------------------------
def test_no_fire_and_forget(tmp_path):
    eng = build_test_sadar(tmp_path, OfflineBackend())
    eng.perceiver.push("simpan ide untuk presentasi")

    eng.tick()

    results = [r for r in eng.d.workspace.items if r.source == "action_result"]
    assert results
    assert all(r.caused_by for r in results), "action_result tanpa jejak kausal = fire-and-forget"


# --- degraded mode: otak S2 mati → loop tetap hidup & jujur --------------------
def test_degraded_mode_when_brain_unavailable(tmp_path):
    class DeadBackend(SilentBackend):
        def available(self) -> bool:                   # otak-dalam tak terjangkau
            return False

    eng = build_test_sadar(tmp_path, DeadBackend())
    eng.perceiver.push("ada sesuatu yang perlu dipikirkan")   # memicu kebutuhan deliberasi

    eng.tick()

    assert eng.d.degraded.active is True
    assert eng.d.degraded.cause == "s2_unreachable"
    assert eng.d.tick_count == 1                        # loop TIDAK mati, hanya menyusut
