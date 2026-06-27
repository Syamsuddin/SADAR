"""Config Doctor (Slice 4.3) — audit postur keamanan, read-only & deterministik."""
from __future__ import annotations

from sadar.config import AppConfig
from sadar.doctor import audit_config, format_report
from sadar.roles.registry import get_role


def test_doctor_flags_full_access():
    f = audit_config(AppConfig(shell={"full_access": True}), get_role("pa"))
    assert any(lvl == "WARN" and "AKSES-PENUH" in msg for lvl, msg in f)


def test_doctor_flags_ssrf_and_remote_store():
    f = audit_config(AppConfig(web={"allow_private": True}, store={"allow_remote": True}), get_role("pa"))
    msgs = " ".join(m for _, m in f)
    assert "SSRF" in msgs and "remote" in msgs


def test_doctor_no_warn_for_readonly_default():
    f = audit_config(AppConfig(), get_role("researcher"))     # read-only + default → tak ada WARN
    assert not any(lvl == "WARN" for lvl, _ in f)


def test_format_report():
    assert "waras" in format_report([])
    rep = format_report([("WARN", "x"), ("INFO", "y")])
    assert "1 WARN" in rep and "1 INFO" in rep
