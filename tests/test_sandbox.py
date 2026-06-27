"""Runtime sandbox (Slice 4.1) — eksekusi shell terisolasi via Docker (defense-in-depth).

Pembentukan perintah Docker SELALU diuji (deterministik); eksekusi nyata di-skip bila Docker absen.
"""
from __future__ import annotations

import shutil
import subprocess

import pytest

from sadar.organs.effector_shell import ShellEffector


def _docker_up() -> bool:
    """Docker dapat dipakai HANYA bila CLI ada DAN daemon aktif (cek `docker info`)."""
    if shutil.which("docker") is None:
        return False
    try:
        return subprocess.run(["docker", "info"], capture_output=True, timeout=8).returncode == 0
    except Exception:  # noqa: BLE001
        return False


def test_docker_argv_is_isolated(tmp_path):
    eff = ShellEffector(workdir=str(tmp_path), full_access=True, sandbox=True, sandbox_image="alpine")
    argv = eff._docker_argv("ls -la")
    assert argv[:5] == ["docker", "run", "--rm", "--network", "none"]    # tanpa jaringan
    assert "--memory" in argv and "--cpus" in argv and "--pids-limit" in argv  # batas sumber daya
    assert f"{tmp_path}:/work" in argv and "-w" in argv                  # hanya workdir ter-mount
    assert argv[-4:] == ["alpine", "sh", "-c", "ls -la"]                 # perintah dibungkus sh -c


@pytest.mark.skipif(not _docker_up(), reason="butuh Docker daemon aktif")
def test_sandbox_executes_in_container(tmp_path):
    eff = ShellEffector(workdir=str(tmp_path), full_access=True, sandbox=True)
    r = eff.act("shell", {"cmd": "echo sadar-sandbox"})
    assert r.ok and "sadar-sandbox" in r.output
