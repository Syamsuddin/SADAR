"""Organ CLI (shell) — gerbang KODE berlapis, semua deterministik.

Membuktikan: allowlist menolak yang tak terdaftar; metakarakter & jalur-biner-eksplisit ditolak
(anti-injeksi); kapabilitas wajib; mutasi WAJIB konfirmasi manusia (HITL); dan SADAR benar-benar
menjalankan perintah baca lewat lingkaran hidup.
"""
from __future__ import annotations

import json
import re

from sadar.config import AppConfig
from sadar.core.constitution import ProposedAction, build_constitution_engine, is_risky_command
from sadar.core.dosir import Dosir
from sadar.core.ports import BackendSpec
from sadar.main import build_sadar
from sadar.organs.effector_shell import ShellEffector


class Scripted:
    def __init__(self, steps):
        self.steps = list(steps)
        self.i = 0

    def complete(self, system, prompt, *, tier="sys2"):
        s = self.steps[min(self.i, len(self.steps) - 1)]
        self.i += 1
        return s

    def spec(self):
        return BackendSpec(name="scripted", provenance="local", trust=0.9,
                           tiers=["sys2"], leaves_premises=False)

    def available(self):
        return True


# ---------------- effector: allowlist + anti-injeksi ----------------
def test_shell_runs_allowed_read_command(tmp_path):
    r = ShellEffector(workdir=str(tmp_path)).act("shell", {"cmd": "echo halo"})
    assert r.ok and "halo" in r.output


def test_shell_rejects_command_not_in_allowlist(tmp_path):
    r = ShellEffector(workdir=str(tmp_path)).act("shell", {"cmd": "rm -rf /"})
    assert not r.ok and "allowlist" in r.output


def test_shell_rejects_metacharacters(tmp_path):
    eff = ShellEffector(workdir=str(tmp_path))
    for bad in ["echo hi; rm x", "echo a | cat", "echo `whoami`",
                "cat x > y", "echo $HOME", "echo a && rm b"]:
        assert not eff.act("shell", {"cmd": bad}).ok, f"harusnya ditolak: {bad}"


def test_shell_rejects_explicit_binary_path(tmp_path):
    assert not ShellEffector(workdir=str(tmp_path)).act("shell", {"cmd": "/bin/ls"}).ok


def test_shell_write_executes_mutating_command(tmp_path):
    r = ShellEffector(workdir=str(tmp_path)).act("shell_write", {"cmd": "mkdir baru"})
    assert r.ok and (tmp_path / "baru").is_dir()


def test_read_tool_cannot_mutate(tmp_path):
    # mkdir bukan di allowlist 'shell' (baca) → ditolak
    assert not ShellEffector(workdir=str(tmp_path)).act("shell", {"cmd": "mkdir x"}).ok


# ---------------- gerbang konstitusi: kapabilitas + HITL ----------------
def test_shell_requires_capability():
    ec = build_constitution_engine()
    a = ProposedAction(tool="shell", args={"cmd": "ls"}, required_caps=["shell.read"])
    assert ec.gate.vet(a, Dosir()).reason == "capability_not_granted"
    d = Dosir()
    d.granted_caps = {"shell.read"}
    assert ec.gate.vet(a, d).allowed


def test_shell_write_requires_human_confirmation():
    ec = build_constitution_engine()
    d = Dosir()
    d.granted_caps = {"shell.write"}
    unconfirmed = ProposedAction(tool="shell_write", args={"cmd": "mkdir x"},
                                 reversible=False, required_caps=["shell.write"])
    assert ec.gate.vet(unconfirmed, d).reason == "hitl_irreversible"
    confirmed = ProposedAction(tool="shell_write", args={"cmd": "mkdir x", "_confirmed": True},
                               reversible=False, required_caps=["shell.write"])
    assert ec.gate.vet(confirmed, d).allowed


# ---------------- lingkaran hidup: SADAR menjalankan perintah baca ----------------
def test_live_loop_runs_shell_command(tmp_path):
    eng = build_sadar(
        AppConfig(store={"root": str(tmp_path / "m")}, shell={"workdir": str(tmp_path)},
                  loop={"tick_interval_s": 0.0}),
        cli=True,
        backend=Scripted([json.dumps(
            {"reasoning": "cek sistem", "action": {"tool": "shell", "args": {"cmd": "echo halo-sadar"}}})]))
    assert "shell" in [t.name for t in eng.effector.list_tools()]
    eng.perceiver.push("apa kabar sistem")
    eng.tick()
    res = [r for r in eng.d.workspace.items if r.source == "action_result"]
    assert res and "halo-sadar" in res[0].content


def test_live_loop_shell_write_waits_for_confirmation(tmp_path):
    eng = build_sadar(
        AppConfig(store={"root": str(tmp_path / "m")}, shell={"workdir": str(tmp_path)},
                  loop={"tick_interval_s": 0.0}),
        cli=True,
        backend=Scripted([json.dumps(
            {"reasoning": "buat folder", "action": {"tool": "shell_write", "args": {"cmd": "mkdir dibuat"}}})]))
    eng.perceiver.push("tolong buatkan folder")
    eng.tick()
    assert not (tmp_path / "dibuat").exists()        # belum dieksekusi
    pend = [r for r in eng.d.workspace.items if "KONFIRMASI DIBUTUHKAN" in r.content]
    assert pend                                       # menunggu persetujuan manusia


# ================= MODE AKSES-PENUH (denylist + konfirmasi, tanpa lantai) =================
def test_risk_classifier_code_only():
    """Klasifikasi risiko murni KODE (Aturan Kardinal #1) — denylist + metakarakter + flag."""
    risky = ["rm file", "sudo ls", "echo a | sh", "cat x > y", "mv a b", "cp a b",
             "curl http://x", "find . -delete", "python -c 'x'", "echo $(whoami)",
             "dd if=/dev/zero of=d", "kill 123", "chmod 777 f", "ls -rf", "git push",
             "echo a && rm b", "echo `id`"]
    safe = ["ls -la", "cat file.txt", "pwd", "echo halo dunia", "grep foo bar",
            "df -h", "whoami", "date", "head -n 5 f", "wc -l f", "uname -a"]
    for c in risky:
        assert is_risky_command(c), f"harusnya berisiko: {c}"
    for c in safe:
        assert not is_risky_command(c), f"harusnya aman: {c}"


def test_full_access_executes_any_command_incl_pipe(tmp_path):
    eff = ShellEffector(workdir=str(tmp_path), full_access=True)
    assert [t.name for t in eff.list_tools()] == ["shell"]      # satu tool tunggal
    r = eff.act("shell", {"cmd": "echo hi | tr a-z A-Z"})       # pipe → butuh shell
    assert r.ok and "HI" in r.output


def test_full_access_gate_risky_needs_confirmation():
    ec = build_constitution_engine()
    d = Dosir()
    d.granted_caps = {"shell.read", "shell.write"}
    d.shell_full_access = True
    caps = ["shell.read", "shell.write"]
    safe = ProposedAction(tool="shell", args={"cmd": "ls -la"}, required_caps=caps)
    assert ec.gate.vet(safe, d).allowed                         # aman → langsung
    risky = ProposedAction(tool="shell", args={"cmd": "rm -rf data"}, required_caps=caps)
    assert ec.gate.vet(risky, d).reason == "hitl_risky_command"  # berisiko → HITL
    ok = ProposedAction(tool="shell", args={"cmd": "rm -rf data", "_confirmed": True}, required_caps=caps)
    assert ec.gate.vet(ok, d).allowed                            # dikonfirmasi → lolos (tanpa lantai)


def test_risk_gate_inactive_when_full_access_off():
    """Tanpa mode akses-penuh, limit risiko TIDAK aktif → model default (allowlist effector) berlaku."""
    ec = build_constitution_engine()
    d = Dosir()
    d.granted_caps = {"shell.read", "shell.write"}              # shell_full_access=False (default)
    risky = ProposedAction(tool="shell", args={"cmd": "rm -rf x"}, required_caps=["shell.read"])
    assert ec.gate.vet(risky, d).allowed                        # gate lolos; effector menolak via allowlist


def test_live_full_access_safe_runs_risky_waits_then_confirm(tmp_path):
    cfg = AppConfig(store={"root": str(tmp_path / "m")},
                    shell={"workdir": str(tmp_path), "full_access": True},
                    loop={"tick_interval_s": 0.0})
    # aman → jalan langsung
    eng = build_sadar(cfg, cli=True, backend=Scripted([json.dumps(
        {"reasoning": "cek", "action": {"tool": "shell", "args": {"cmd": "echo sadar-ok"}}})]))
    eng.perceiver.push("cek")
    eng.tick()
    res = [r for r in eng.d.workspace.items if r.source == "action_result"]
    assert res and "sadar-ok" in res[0].content
    # berisiko → ditahan HITL, lalu confirm → dieksekusi
    (tmp_path / "data").mkdir()
    eng2 = build_sadar(cfg, cli=True, backend=Scripted([json.dumps(
        {"reasoning": "hapus", "action": {"tool": "shell", "args": {"cmd": "rm -rf data"}}})]))
    eng2.perceiver.push("hapus folder data")
    eng2.tick()
    assert (tmp_path / "data").exists()                         # belum dieksekusi (menunggu izin)
    pend = [r for r in eng2.d.workspace.items if "KONFIRMASI DIBUTUHKAN" in r.content]
    assert pend
    rid = re.search(r"id=([0-9a-f]+)", pend[0].content).group(1)
    eng2.confirm(rid)
    assert not (tmp_path / "data").exists()                     # setelah konfirmasi → terhapus
