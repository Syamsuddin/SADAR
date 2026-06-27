"""Permission model + registry Peran (Fase C) — multi-purpose dengan keamanan berskala.

Membuktikan: (a) gerbang kapabilitas deterministik; (b) Peran read-only (researcher) tak bisa
menulis/menghapus walau otak mengusulkannya — NOL perubahan di sadar/core/; (c) tetap bisa
membaca/recall; (d) Peran PA (default) bisa menulis. Mekanisme keselamatan identik lintas-peran.
"""
from __future__ import annotations

import pytest

from sadar.config import AppConfig
from sadar.core.constitution import ProposedAction, build_constitution_engine
from sadar.core.dosir import Dosir
from sadar.core.ports import MemoryItem
from sadar.main import build_sadar
from sadar.roles.registry import get_role
from sadar.roles.researcher.role import RESEARCHER_ROLE
from tests.mocks import FabricatingBackend


def _eng(tmp_path, backend, role):
    return build_sadar(AppConfig(store={"root": str(tmp_path / "m")}, loop={"tick_interval_s": 0.0}),
                       backend=backend, role=role)


# --- gerbang kapabilitas (unit, deterministik) ---
def test_capability_not_granted_vetoes():
    ec = build_constitution_engine()
    d = Dosir()
    d.granted_caps = {"notes.read"}
    v = ec.gate.vet(ProposedAction(tool="note_create", required_caps=["notes.write"]), d)
    assert not v.allowed and v.reason == "capability_not_granted"
    d.granted_caps = {"notes.write"}
    assert ec.gate.vet(ProposedAction(tool="note_create", required_caps=["notes.write"]), d).allowed


def test_registry_resolves_roles():
    assert get_role("pa").granted_caps >= {"notes.write"}
    assert get_role("researcher").granted_caps == {"notes.read"}
    with pytest.raises(ValueError):
        get_role("nope")


# --- Peran read-only TIDAK bisa menulis (tesis buta-platform: nol perubahan inti) ---
def test_researcher_role_cannot_write(tmp_path):
    eng = _eng(tmp_path, FabricatingBackend(
        '{"reasoning":"catat","action":{"tool":"note_create","args":{"text":"x"}}}'), RESEARCHER_ROLE)
    eng.perceiver.push("tolong catat sesuatu")
    eng.tick()
    veto = [r for r in eng.d.workspace.items if "VETO" in r.content]
    assert veto and "capability_not_granted" in veto[0].content
    assert not [r for r in eng.d.workspace.items if r.source == "action_result"]   # tak ada penulisan


# --- Peran read-only TETAP bisa membaca/recall ---
def test_researcher_role_can_recall(tmp_path):
    eng = _eng(tmp_path, FabricatingBackend(
        '{"reasoning":"cari","action":{"tool":"recall","args":{"query":"paspor"}}}'), RESEARCHER_ROLE)
    eng.memory.store.write(MemoryItem(content="paspor ada di laci atas"))
    eng.perceiver.push("di mana paspor?")
    eng.tick()
    res = [r for r in eng.d.workspace.items if r.source == "action_result"]
    assert res and "paspor" in res[0].content


# --- Peran PA (default) bisa menulis ---
def test_pa_role_can_write(tmp_path):
    eng = _eng(tmp_path, FabricatingBackend(
        '{"reasoning":"catat","action":{"tool":"note_create","args":{"text":"beli kopi"}}}'),
        get_role("pa"))
    eng.perceiver.push("catat: beli kopi")
    eng.tick()
    assert any("beli kopi" in (eng.memory.store.read(i).content or "")
               for i in eng.memory.store.list())
