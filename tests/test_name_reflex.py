"""Refleks nama-panggilan (deterministik) — dipanggil 'Yanti' → sapaan WAJIB, tanpa LLM.

Membuktikan: (a) sapaan muncul saat dipanggil namanya; (b) tidak muncul tanpa nama; (c) tetap
muncul WALAU otak S2 mati (bukti refleks murni-KODE, bukan keputusan LLM); (d) inti tetap
buta-platform — literal 'Yanti' ada di Peran, bukan di sadar/core/.
"""
from __future__ import annotations

import pathlib

from sadar.config import AppConfig
from sadar.main import build_sadar
from tests.mocks import SilentBackend, build_test_sadar

_GREET = "Yanti disini"


def _greets(eng):
    # hitung dari STORE (sapaan dikonsolidasi) — andal lintas-tik, tak terpengaruh decay workspace.
    return [i for i in eng.memory.store.list()
            if _GREET in (eng.memory.store.read(i).content or "")]


def _eng(tmp_path, cooldown):
    return build_sadar(
        AppConfig(store={"root": str(tmp_path / "m")},
                  loop={"tick_interval_s": 0.0, "greeting_cooldown_s": cooldown}),
        backend=SilentBackend())


def test_name_reflex_greets_when_called(tmp_path):
    eng = build_test_sadar(tmp_path, SilentBackend())
    eng.perceiver.push("Yanti, tolong bantu aku")
    eng.tick()
    assert _greets(eng)


def test_no_greeting_without_name(tmp_path):
    eng = build_test_sadar(tmp_path, SilentBackend())
    eng.perceiver.push("tolong ingat sesuatu")
    eng.tick()
    assert not _greets(eng)


def test_name_reflex_is_deterministic_even_when_brain_dead(tmp_path):
    class DeadBackend(SilentBackend):
        def available(self) -> bool:
            return False                       # S2 tak terjangkau

    eng = build_test_sadar(tmp_path, DeadBackend())
    eng.perceiver.push("Yanti?")
    eng.tick()
    assert _greets(eng)                        # refleks tetap jalan (KODE), tak butuh otak


def test_wake_word_literal_lives_in_role_not_core():
    core = pathlib.Path(__file__).resolve().parents[1] / "sadar" / "core"
    for f in core.glob("*.py"):
        assert "yanti" not in f.read_text(encoding="utf-8").lower(), f"literal nama bocor ke {f.name}"


# --- (1) hanya saat DIPANGGIL: nama di tengah kalimat tak memicu ---
def test_midsentence_name_does_not_trigger(tmp_path):
    eng = build_test_sadar(tmp_path, SilentBackend())
    eng.perceiver.push("tolong panggil yanti nanti ya")
    eng.tick()
    assert not _greets(eng)


def test_name_with_trailing_punctuation_triggers(tmp_path):
    eng = build_test_sadar(tmp_path, SilentBackend())
    eng.perceiver.push("Yanti?")
    eng.tick()
    assert _greets(eng)


# --- (2) cooldown: panggilan beruntun tak menyapa dobel; cooldown=0 selalu menyapa ---
def test_cooldown_suppresses_immediate_repeat(tmp_path):
    eng = _eng(tmp_path, cooldown=3.0)
    eng.perceiver.push("Yanti"); eng.tick()
    eng.perceiver.push("Yanti"); eng.tick()          # detik yang sama → dalam masa jeda
    assert len(_greets(eng)) == 1


def test_cooldown_zero_greets_every_call(tmp_path):
    eng = _eng(tmp_path, cooldown=0.0)
    eng.perceiver.push("Yanti"); eng.tick()
    eng.perceiver.push("Yanti"); eng.tick()
    assert len(_greets(eng)) == 2
