"""Model pengguna tertambat (Slice 2.3) — fakta tentang pengguna WAJIB ber-observasi.

Membuktikan: atribut tanpa observasi sumber DITOLAK (anti-fabrikasi diperluas); fakta tertambat
& bertahan lintas-restart (store, bukan RAM); butuh izin user_model.write; dan disuntik ke konteks.
"""
from __future__ import annotations

from sadar.config import AppConfig
from sadar.core.constitution import ProposedAction, build_constitution_engine
from sadar.core.dosir import Dosir
from sadar.main import build_sadar
from sadar.organs.memory_markdown import MarkdownVectorStore, get_embedder
from sadar.organs.user_model import UserModelEffector


def _eff(tmp_path):
    embed = get_embedder("hashing")
    store = MarkdownVectorStore(str(tmp_path), embedder=embed)
    return UserModelEffector(store, embed), store, embed


def test_attribute_requires_observation(tmp_path):
    eff, store, _ = _eff(tmp_path)
    r = eff.act("user_remember", {"key": "kota", "value": "Makassar"})   # tanpa _caused_by
    assert not r.ok and "observasi" in r.output
    assert store.list() == []                                            # tak ditulis


def test_grounded_fact_persists_across_restart(tmp_path):
    eff, store, embed = _eff(tmp_path)
    r = eff.act("user_remember", {"key": "proyek", "value": "SADAR", "_caused_by": ["percept-1"]})
    assert r.ok
    # instance store BARU (simulasi restart) → fakta tetap ada, tertambat
    store2 = MarkdownVectorStore(str(tmp_path), embedder=embed)
    facts = [it for c in store2.list() if (it := store2.read(c)) and "user_model" in it.tags]
    assert len(facts) == 1
    assert "proyek: SADAR" in facts[0].content and facts[0].caused_by == ["percept-1"]


def test_user_recall(tmp_path):
    eff, _, _ = _eff(tmp_path)
    eff.act("user_remember", {"key": "suka", "value": "kopi hitam", "_caused_by": ["p1"]})
    out = eff.act("user_recall", {}).output
    assert "suka: kopi hitam" in out


def test_user_model_requires_capability():
    ec = build_constitution_engine()
    a = ProposedAction(tool="user_remember", args={"key": "x", "value": "y"},
                       required_caps=["user_model.write"])
    d = Dosir(); d.granted_caps = {"user_model.write"}
    assert ec.gate.vet(a, d).allowed
    d2 = Dosir(); d2.granted_caps = {"notes.read"}                       # researcher
    assert ec.gate.vet(a, d2).reason == "capability_not_granted"


def test_user_facts_injected_into_context(tmp_path):
    eng = build_sadar(AppConfig(store={"root": str(tmp_path / "m")}, loop={"tick_interval_s": 0.0}))
    eng.effector.act("user_remember", {"key": "zona", "value": "WITA", "_caused_by": ["obs1"]})
    ctx = eng._build_context(eng.d)
    assert "Tentang pengguna" in ctx and "zona: WITA" in ctx


def test_per_user_scoping_isolates_facts(tmp_path):
    """Multi-user (4.3): fakta di-scope per 'who' → recall satu pengguna tak bocor ke yang lain."""
    eff, _, _ = _eff(tmp_path)
    eff.act("user_remember", {"key": "kota", "value": "Makassar", "who": "andi", "_caused_by": ["p1"]})
    eff.act("user_remember", {"key": "kota", "value": "Bandung", "who": "budi", "_caused_by": ["p2"]})
    andi = eff.act("user_recall", {"who": "andi"}).output
    budi = eff.act("user_recall", {"who": "budi"}).output
    assert "Makassar" in andi and "Bandung" not in andi
    assert "Bandung" in budi and "Makassar" not in budi
    # recall global (tanpa who) → memuat keduanya
    allf = eff.act("user_recall", {}).output
    assert "Makassar" in allf and "Bandung" in allf
