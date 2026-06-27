"""Anti-fabrikasi KLAIM-DUNIA (frontier) — fakta yang diucapkan SADAR ditambat ke OBSERVASInya.

Membuktikan: rincian spesifik (angka/jalur) yang TAK ada di evidence & tak di-hedge → ditandai
"belum terverifikasi"; rincian yang tertambat ke observasi → lolos; kalimat ber-hedge & konversasional
tak diganggu. CATATAN: ini menambat ke 'yang kuamati', BUKAN verifikasi kebenaran (mustahil).
"""
from __future__ import annotations

import json

from sadar.config import AppConfig
from sadar.core.constitution import unsupported_world_claims
from sadar.core.ports import BackendSpec
from sadar.main import build_sadar


# ---- unit: penambat murni ----
def test_ungrounded_specifics_flagged():
    out = unsupported_world_claims("Berkasnya di /opt/rahasia, ukuran 4096 byte.", evidence="")
    assert "/opt/rahasia" in out and "4096" in out


def test_grounded_specifics_pass():
    ev = "hasil alat: $ ls /opt/rahasia → 4096 byte"
    assert unsupported_world_claims("Berkasnya di /opt/rahasia, 4096 byte.", ev) == []


def test_hedged_sentence_skipped():
    assert unsupported_world_claims("Mungkin sekitar 4096 byte.", evidence="") == []
    assert unsupported_world_claims("Kira-kira di /opt/rahasia [umum].", evidence="") == []


def test_conversational_not_flagged():
    assert unsupported_world_claims("Ada yang bisa saya bantu, Pak Syam?", evidence="") == []
    assert unsupported_world_claims("Tugas saya membantu Anda.", evidence="") == []


def test_single_digit_not_specific():
    assert unsupported_world_claims("Langkah 1 selesai.", evidence="") == []   # 1 digit → bukan rincian


# ---- integrasi: reply lewat lingkaran ----
class Scripted:
    def __init__(self, reply):
        self.reply = reply

    def complete(self, system, prompt, *, tier="sys2"):
        return json.dumps({"reasoning": "x", "reply": self.reply, "action": None})

    def spec(self):
        return BackendSpec(name="s", provenance="local", trust=0.9, tiers=["sys2"], leaves_premises=False)

    def available(self):
        return True


def _reply_text(eng):
    reps = [r.content for r in eng.d.workspace.items
            if r.source == "thought" and r.content.startswith("[reply]")]
    return reps[-1] if reps else ""


def test_ungrounded_reply_gets_honest_disclaimer(tmp_path):
    eng = build_sadar(AppConfig(store={"root": str(tmp_path / "m")}, loop={"tick_interval_s": 0.0}),
                      backend=Scripted("Berkasmu ada di /var/data/x dan berukuran 9090 byte."))
    eng.perceiver.push("di mana berkasku?")
    eng.tick()
    rep = _reply_text(eng)
    assert "belum terverifikasi" in rep and "/var/data/x" in rep   # ditandai jujur, rincian disebut


def test_grounded_reply_no_disclaimer(tmp_path):
    eng = build_sadar(AppConfig(store={"root": str(tmp_path / "m")}, loop={"tick_interval_s": 0.0}),
                      backend=Scripted("Baik, port 8080 sudah kucatat."))
    eng.perceiver.push("catat port 8080 untuk server")   # 8080 jadi observasi (persepsi)
    eng.tick()
    assert "belum terverifikasi" not in _reply_text(eng)
