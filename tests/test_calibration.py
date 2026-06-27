"""Kalibrasi angka (Slice 4.4) — default `config.py` menjaga lingkaran HIDUP & waras.

Regresi: default tak boleh membuat loop macet, over-deliberasi, atau menguras energi seketika.
"""
from __future__ import annotations

from sadar.config import AppConfig
from sadar.organs.backend_offline import OfflineBackend


def _eng(tmp_path):
    from sadar.main import build_sadar
    return build_sadar(AppConfig(store={"root": str(tmp_path / "m")}, loop={"tick_interval_s": 0.0}),
                       backend=OfflineBackend())


def test_default_thresholds_keep_loop_live(tmp_path):
    eng = _eng(tmp_path)
    for _ in range(30):
        eng.tick()                                  # banyak tik sepi → tak macet/crash
    s = eng.d.snapshot()
    assert eng.d.tick_count == 30
    assert not s["shutdown_requested"]
    assert 0.5 < s["energy"] <= 1.0                 # decay 0.005/tik → ~0.85, tak habis seketika
    assert 0.0 <= s["confidence"] <= 1.0 and 0.0 <= s["integration"] <= 1.0


def test_input_triggers_bounded_response(tmp_path):
    eng = _eng(tmp_path)
    eng.perceiver.push("tolong catat: beli kopi")
    eng.tick()
    # input → deliberasi terpicu, mencatat; workspace tetap terbatas (tak meledak)
    assert len(eng.d.workspace.items) < 50
    assert any(r.source == "action_result" for r in eng.d.workspace.items)
