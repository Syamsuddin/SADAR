"""Tool Draft (Fase 3) — otak mengusulkan tool baru sebagai DOKUMEN INERT untuk ditinjau manusia.

Membuktikan: usulan tersimpan tapi INERT; tool yang diusulkan TIDAK auto-aktif di lingkaran
(Aturan Kardinal #1); dan mengusulkan butuh izin tool.draft (read-only role tak bisa).
"""
from __future__ import annotations

from sadar.config import AppConfig
from sadar.core.constitution import ProposedAction, build_constitution_engine
from sadar.core.dosir import Dosir
from sadar.main import build_sadar
from sadar.organs.proposal_store import ProposalStore
from sadar.organs.tool_draft import ToolDraftEffector


def test_propose_writes_inert_document(tmp_path):
    eff = ToolDraftEffector(ProposalStore(str(tmp_path)))
    r = eff.act("tool_propose", {
        "name": "web_fetch", "purpose": "membaca isi URL",
        "required_caps": ["web.read"], "code": "class WebFetchEffector: ...",
        "notes": "risiko: keluar premis (network)"})
    assert r.ok and "DRAFT" in r.output and "TIDAK aktif" in r.output
    p = ProposalStore(str(tmp_path)).read("web_fetch")
    assert p is not None and p.status == "proposed" and p.author == "conversation"
    assert "```python" in p.body and "web.read" in p.body          # kode + izin terekam (inert)
    assert p.required_caps == ["web.read"]


def test_proposed_tool_NOT_auto_activated(tmp_path):
    """Kardinal #1: mengusulkan tool TIDAK membuatnya tersedia di lingkaran."""
    eng = build_sadar(AppConfig(store={"root": str(tmp_path / "m")},
                                proposals={"root": str(tmp_path / "p")},
                                loop={"tick_interval_s": 0.0}))
    assert "tool_propose" in eng._tools                            # meta-tool ada
    eng.effector.act("tool_propose", {"name": "web_fetch", "purpose": "x",
                                      "required_caps": ["web.read"], "code": "..."})
    assert "web_fetch" not in eng._tools                           # TAPI tool usulan TAK muncul
    assert ProposalStore(str(tmp_path / "p")).read("web_fetch") is not None  # hanya jadi dokumen


def test_propose_requires_capability():
    ec = build_constitution_engine()
    a = ProposedAction(tool="tool_propose", args={"name": "x"}, required_caps=["tool.draft"])
    d = Dosir(); d.granted_caps = {"tool.draft"}
    assert ec.gate.vet(a, d).allowed                               # PA punya izin → boleh draft
    d2 = Dosir(); d2.granted_caps = {"notes.read"}                 # researcher
    assert ec.gate.vet(a, d2).reason == "capability_not_granted"   # tanpa izin → veto


def test_tool_proposals_list(tmp_path):
    eff = ToolDraftEffector(ProposalStore(str(tmp_path)))
    assert "belum ada" in eff.act("tool_proposals", {}).output
    eff.act("tool_propose", {"name": "kalender", "purpose": "p"})
    out = eff.act("tool_proposals", {}).output
    assert "kalender" in out and "proposed" in out
