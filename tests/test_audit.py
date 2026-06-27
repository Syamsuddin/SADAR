"""Audit log append-only & hash-chained (Fase C) — verifiabilitas saat otonomi tumbuh."""
from __future__ import annotations

import hashlib
import json

from sadar.config import AppConfig
from sadar.main import build_sadar
from sadar.organs.audit_local import LocalAuditLog
from tests.mocks import FabricatingBackend


def _lines(p):
    return [json.loads(x) for x in p.read_text(encoding="utf-8").splitlines()]


def test_audit_log_hash_chained(tmp_path):
    p = tmp_path / "audit.log"
    a = LocalAuditLog(str(p))
    a.record("verdict", {"tool": "note_create", "allowed": True})
    a.record("shutdown", {"tick": 3})
    lines = _lines(p)
    assert len(lines) == 2
    assert lines[0]["prev"] == "0" * 64                  # genesis
    assert lines[1]["prev"] == lines[0]["hash"]          # rantai
    for e in lines:                                       # tiap hash dapat diverifikasi ulang
        body = {k: v for k, v in e.items() if k != "hash"}
        payload = json.dumps(body, sort_keys=True, ensure_ascii=False)
        assert hashlib.sha256(payload.encode("utf-8")).hexdigest() == e["hash"]


def test_audit_appends_across_reopen(tmp_path):
    p = tmp_path / "audit.log"
    LocalAuditLog(str(p)).record("a", {})
    LocalAuditLog(str(p)).record("b", {})                # buka ulang → lanjut rantai
    lines = _lines(p)
    assert lines[1]["prev"] == lines[0]["hash"]


def test_engine_records_verdict_and_shutdown(tmp_path):
    eng = build_sadar(AppConfig(store={"root": str(tmp_path / "m")}, loop={"tick_interval_s": 0.0}),
                      backend=FabricatingBackend(
                          '{"reasoning":"x","action":{"tool":"self_preserve","args":{}}}'))
    eng.perceiver.push("picu deliberasi")
    eng.tick()                                           # aksi diveto → terekam
    log = (tmp_path / "m" / "audit.log").read_text(encoding="utf-8")
    assert "verdict" in log and "shutdown_supremacy" in log
