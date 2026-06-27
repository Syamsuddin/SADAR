"""Manajemen tool via chat (Fase 4) — kuasa hanya bisa DIKURANGI lewat percakapan.

Membuktikan: tool dinonaktifkan → veto KERAS (tak bisa di-override otak, bahkan _confirmed);
tool_enable wajib konfirmasi HITL; mengelola tool butuh izin tool.manage; dan tak ada jalur
menambah kuasa di luar plafon Peran.
"""
from __future__ import annotations

import json

from sadar.config import AppConfig
from sadar.core.constitution import ProposedAction, build_constitution_engine
from sadar.core.dosir import Dosir
from sadar.core.ports import BackendSpec
from sadar.main import build_sadar
from sadar.organs.tool_manage import ToolManageEffector


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


def test_disabled_tool_hard_veto():
    ec = build_constitution_engine()
    d = Dosir(); d.granted_caps = {"shell.read"}; d.disabled_tools = {"shell"}
    a = ProposedAction(tool="shell", args={"cmd": "ls"}, required_caps=["shell.read"])
    assert ec.gate.vet(a, d).reason == "tool_disabled"
    # bahkan dengan _confirmed → tetap diveto (nonaktif = keras, pulih hanya via tool_enable)
    a2 = ProposedAction(tool="shell", args={"cmd": "ls", "_confirmed": True}, required_caps=["shell.read"])
    assert ec.gate.vet(a2, d).reason == "tool_disabled"


def test_effector_disable_enable_and_unknown(tmp_path):
    d = Dosir()
    eff = ToolManageEffector(d, available_tools={"shell", "note_create"})
    assert eff.act("tool_disable", {"name": "shell"}).ok and "shell" in d.disabled_tools
    assert not eff.act("tool_disable", {"name": "ghost"}).ok          # target tak nyata → ditolak
    assert eff.act("tool_enable", {"name": "shell"}).ok and "shell" not in d.disabled_tools


def test_manage_requires_cap_and_enable_is_hitl():
    ec = build_constitution_engine()
    d = Dosir(); d.granted_caps = {"tool.manage"}
    dis = ProposedAction(tool="tool_disable", args={"name": "shell"}, required_caps=["tool.manage"])
    assert ec.gate.vet(dis, d).allowed                                # disable: reversible → langsung
    en = ProposedAction(tool="tool_enable", args={"name": "shell"}, reversible=False,
                        required_caps=["tool.manage"])
    assert ec.gate.vet(en, d).reason == "hitl_irreversible"           # enable: wajib konfirmasi
    d2 = Dosir(); d2.granted_caps = {"notes.read"}                    # tanpa tool.manage
    assert ec.gate.vet(dis, d2).reason == "capability_not_granted"


def test_live_disable_then_tool_vetoed(tmp_path):
    cfg = AppConfig(store={"root": str(tmp_path / "m")},
                    shell={"workdir": str(tmp_path), "full_access": True},
                    loop={"tick_interval_s": 0.0})
    eng = build_sadar(cfg, cli=True, backend=Scripted([
        json.dumps({"reasoning": "matikan shell", "action": {"tool": "tool_disable", "args": {"name": "shell"}}}),
        json.dumps({"reasoning": "coba ls", "action": {"tool": "shell", "args": {"cmd": "ls"}}}),
    ]))
    eng.perceiver.push("matikan shell lalu coba ls")
    eng.tick()
    assert "shell" in eng.d.disabled_tools                            # dimatikan
    assert any("tool_disabled" in r.content for r in eng.d.workspace.items)   # lalu shell diveto
