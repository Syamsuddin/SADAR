"""SkillStore (Fase 1) — kompetensi markdown + capability firewall + injeksi konteks.

Membuktikan: parse/serialisasi roundtrip; FIREWALL (skill aktif hanya bila caps+tool dipenuhi);
CRUD berkas; dan skill aktif benar-benar masuk konteks deliberasi (lapis-3 hidup).
"""
from __future__ import annotations

from sadar.config import AppConfig
from sadar.main import build_sadar
from sadar.organs.skill_store import Skill, SkillStore, parse_skill_md, skill_to_md
from sadar.roles.registry import get_role


def test_parse_roundtrip():
    sk = Skill(name="demo", description="Contoh.", know_how="Langkah 1.", when="saat X",
               tools=["recall", "note_create"], required_caps=["notes.read", "notes.write"],
               author="conversation")
    again = parse_skill_md(skill_to_md(sk))
    assert again.name == "demo"
    assert again.tools == ["recall", "note_create"]
    assert again.required_caps == ["notes.read", "notes.write"]
    assert again.when == "saat X"
    assert "Langkah 1." in again.know_how
    assert again.author == "conversation"


def test_firewall_caps_and_tools():
    sk = Skill(name="x", tools=["note_create"], required_caps=["notes.write"])
    assert sk.is_active({"notes.write"}, {"note_create"})          # caps+tool ada → aktif
    assert not sk.is_active({"notes.read"}, {"note_create"})       # cap kurang → inactive
    assert not sk.is_active({"notes.write"}, {"recall"})           # tool tak tersedia → inactive
    sk.status = "inactive"
    assert not sk.is_active({"notes.write"}, {"note_create"})      # status mati → inactive


def test_store_crud(tmp_path):
    st = SkillStore(str(tmp_path))
    assert st.list() == []
    st.write(Skill(name="Tinjauan Mingguan", description="rekap", tools=["recall"],
                   required_caps=["notes.read"], author="conversation"))
    names = [s.name for s in st.list()]
    assert "Tinjauan Mingguan" in names
    assert st.read("Tinjauan Mingguan").author == "conversation"
    assert st.delete("Tinjauan Mingguan") is True
    assert st.list() == []


def test_builtin_skills_loaded_for_pa():
    eng = build_sadar(AppConfig(loop={"tick_interval_s": 0.0}), role=get_role("pa"))
    names = {s.name for s in eng.d.skills}
    assert {"notes", "recall"} <= names                            # builtin markdown termuat
    ctx = eng._build_context(eng.d)
    assert "Kompetensi" in ctx and "notes" in ctx                  # lapis-3 hidup: masuk konteks


def test_firewall_excludes_skill_for_readonly_role():
    """Researcher (hanya notes.read) → skill 'notes' (butuh write/delete) TIDAK aktif; 'recall' aktif."""
    eng = build_sadar(AppConfig(loop={"tick_interval_s": 0.0}), role=get_role("researcher"))
    names = {s.name for s in eng.d.skills}
    assert "recall" in names
    assert "notes" not in names                                    # firewall kapabilitas bekerja
