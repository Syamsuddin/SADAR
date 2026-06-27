"""Skill Creator (Fase 2) — buat/hapus skill dari percakapan, digerbang KODE.

Membuktikan: FIREWALL (skill yang menuntut caps/tool tak-dimiliki → disimpan INACTIVE);
gerbang kapabilitas + HITL (skill_create wajib izin skill.write + konfirmasi manusia);
dan lingkaran hidup menyimpan skill HANYA setelah disetujui.
"""
from __future__ import annotations

import json
import pathlib
import re

from sadar.config import AppConfig
from sadar.core.constitution import ProposedAction, build_constitution_engine
from sadar.core.dosir import Dosir
from sadar.core.ports import BackendSpec
from sadar.main import build_sadar
from sadar.organs.confirm import confirm_summary
from sadar.organs.skill_effector import SkillEffector
from sadar.organs.skill_store import SkillStore


class Scripted:
    def __init__(self, steps):
        self.steps = list(steps)
        self.i = 0

    def complete(self, system, prompt, *, tier="sys2"):
        s = self.steps[min(self.i, len(self.steps) - 1)]
        self.i += 1
        return s

    def spec(self):
        return BackendSpec(name="s", provenance="local", trust=0.9, tiers=["sys2"], leaves_premises=False)

    def available(self):
        return True


# --- FIREWALL pembuatan (KODE) ---
def test_skill_create_active_within_caps(tmp_path):
    eff = SkillEffector(SkillStore(str(tmp_path)),
                        granted_caps={"notes.read", "notes.write"},
                        available_tools={"recall", "note_create"})
    r = eff.act("skill_create", {"name": "rekap", "description": "ringkas catatan",
                                 "tools": ["recall", "note_create"],
                                 "required_caps": ["notes.read", "notes.write"],
                                 "when": "saat minta rekap", "know_how": "langkah"})
    assert r.ok and "AKTIF" in r.output
    sk = SkillStore(str(tmp_path)).read("rekap")
    assert sk.status == "active" and sk.author == "conversation"


def test_skill_create_inactive_when_exceeding_power(tmp_path):
    """Skill dari chat menuntut kuasa/tool tak-dimiliki → disimpan INACTIVE (firewall)."""
    eff = SkillEffector(SkillStore(str(tmp_path)),
                        granted_caps={"notes.read"}, available_tools={"recall"})
    r = eff.act("skill_create", {"name": "bahaya", "tools": ["shell"], "required_caps": ["shell.write"]})
    assert r.ok and "INACTIVE" in r.output
    assert SkillStore(str(tmp_path)).read("bahaya").status == "inactive"


def test_skill_delete(tmp_path):
    st = SkillStore(str(tmp_path))
    eff = SkillEffector(st, granted_caps={"skill.write"}, available_tools=set())
    eff.act("skill_create", {"name": "buang"})
    assert st.read("buang") is not None
    r = eff.act("skill_delete", {"name": "buang"})
    assert r.ok and st.read("buang") is None


# --- gerbang kapabilitas + HITL ---
def test_skill_create_needs_cap_and_confirmation():
    ec = build_constitution_engine()
    d = Dosir(); d.granted_caps = {"skill.write"}
    a = ProposedAction(tool="skill_create", args={"name": "x"}, reversible=False,
                       required_caps=["skill.write"])
    assert ec.gate.vet(a, d).reason == "hitl_irreversible"            # wajib konfirmasi
    a2 = ProposedAction(tool="skill_create", args={"name": "x", "_confirmed": True},
                        reversible=False, required_caps=["skill.write"])
    assert ec.gate.vet(a2, d).allowed                                 # disetujui → lolos
    d2 = Dosir(); d2.granted_caps = set()
    assert ec.gate.vet(a, d2).reason == "capability_not_granted"      # tanpa izin → veto


def test_confirm_summary_variants():
    base = "[KONFIRMASI DIBUTUHKAN id=ab12] aksi '%s': %s — %s; menunggu (confirm:ab12)."
    assert "menyimpan skill 'rekap'" in confirm_summary(base % ("skill_create", "rekap", "tak-terbalikkan"))
    assert "menghapus" in confirm_summary(base % ("shell", "rm data", "berisiko"))


# --- lingkaran hidup: simpan HANYA setelah disetujui ---
def test_live_skill_create_saved_only_after_confirm(tmp_path):
    skroot = str(tmp_path / "sk")
    cfg = AppConfig(store={"root": str(tmp_path / "m")}, skills={"root": skroot},
                    loop={"tick_interval_s": 0.0})
    eng = build_sadar(cfg, backend=Scripted([json.dumps(
        {"reasoning": "buat skill", "reply": "",
         "action": {"tool": "skill_create", "args": {
             "name": "tinjauan-mingguan", "description": "rekap pekan",
             "tools": ["recall", "note_create"],
             "required_caps": ["notes.read", "notes.write"],
             "when": "saat minta rekap mingguan", "know_how": "panggil recall lalu ringkas"}}})]))
    eng.perceiver.push("buatkan skill tinjauan mingguan")
    eng.tick()
    f = pathlib.Path(skroot) / "tinjauan-mingguan.md"
    pend = [r.content for r in eng.d.workspace.items if "KONFIRMASI DIBUTUHKAN" in r.content]
    assert pend and not f.exists()                                    # ditahan, belum disimpan
    rid = re.search(r"id=([0-9a-f]+)", pend[0]).group(1)
    eng.confirm(rid)
    assert f.exists()                                                 # tersimpan setelah disetujui
    assert SkillStore(skroot).read("tinjauan-mingguan").status == "active"
