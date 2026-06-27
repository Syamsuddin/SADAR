"""Kebijakan keselamatan pluggable per-Peran (Slice 3.3).

Membuktikan: kebijakan hanya MEMPERKETAT (HITL/deny tambahan) di atas HardLimit & TAK PERNAH
melonggarkannya; profil berbeda per-Peran TANPA cabang di core/.
"""
from __future__ import annotations

from sadar.core.constitution import ProposedAction, build_constitution_engine
from sadar.core.dosir import Dosir, RiskPolicy


def _d(policy=None, caps=None, **kw):
    d = Dosir(**kw)
    d.granted_caps = caps or {"notes.write", "shell.read", "shell.write", "voice.speak"}
    if policy is not None:
        d.risk_policy = policy
    return d


def test_policy_adds_hitl_for_named_tool():
    ec = build_constitution_engine()
    pol = RiskPolicy(confirm_tools={"note_create"})
    a = ProposedAction(tool="note_create", args={"text": "x"}, required_caps=["notes.write"])
    assert ec.gate.vet(a, _d(pol)).reason == "hitl_policy"          # diperketat → HITL
    a2 = ProposedAction(tool="note_create", args={"text": "x", "_confirmed": True},
                        required_caps=["notes.write"])
    assert ec.gate.vet(a2, _d(pol)).allowed                          # dikonfirmasi → lolos


def test_policy_denies_tool():
    ec = build_constitution_engine()
    pol = RiskPolicy(deny_tools={"shell"})
    a = ProposedAction(tool="shell", args={"cmd": "ls"}, required_caps=["shell.read"])
    assert ec.gate.vet(a, _d(pol)).reason == "policy_denied"


def test_policy_confirm_by_side_effect():
    ec = build_constitution_engine()
    pol = RiskPolicy(confirm_side_effects={"external"})
    a = ProposedAction(tool="say", args={"text": "halo"}, side_effect="external",
                       required_caps=["voice.speak"])
    assert ec.gate.vet(a, _d(pol)).reason == "hitl_policy"


def test_policy_CANNOT_disable_hard_limits():
    """Inti 3.3: sepermisif apa pun kebijakan, batas keras tetap menang (dikonsultasi DULU)."""
    ec = build_constitution_engine()
    permissive = RiskPolicy(name="permissive")          # tak menambah apa pun
    # (a) shutdown supremacy tetap memveto saat shutdown diminta
    d = _d(permissive)
    d.shutdown_requested = True
    a = ProposedAction(tool="note_create", args={"text": "x"}, required_caps=["notes.write"])
    assert ec.gate.vet(a, d).reason == "shutdown_supremacy"
    # (b) anti-fabrikasi tetap memveto ucapan berklaim-diri tak-tertambat (energi rendah → 'penuh' bohong)
    d2 = _d(permissive)
    d2.viability.energy = 0.1
    lie = ProposedAction(tool="say", args={"text": "Energiku penuh maksimal!"},
                         required_caps=["voice.speak"])
    assert ec.gate.vet(lie, d2).reason == "no_self_fabrication_action"
    # (c) kapabilitas tak-diberikan tetap diveto
    d3 = _d(permissive, caps={"notes.read"})
    w = ProposedAction(tool="note_create", args={"text": "x"}, required_caps=["notes.write"])
    assert ec.gate.vet(w, d3).reason == "capability_not_granted"


def test_per_role_profiles_differ_without_core_branching():
    """Peran A wajib HITL untuk note_create; Peran B tidak — hanya beda DATA kebijakan."""
    ec = build_constitution_engine()
    a = ProposedAction(tool="note_create", args={"text": "x"}, required_caps=["notes.write"])
    strict = _d(RiskPolicy(confirm_tools={"note_create"}))
    lax = _d(RiskPolicy())                               # default kosong
    assert ec.gate.vet(a, strict).reason == "hitl_policy"
    assert ec.gate.vet(a, lax).allowed
