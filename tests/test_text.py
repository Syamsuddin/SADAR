"""Chat TEKS — kanal I/O baru di atas lingkaran yang sama. Membuktikan: jawaban 'reply' tampil,
dan perintah CLI berisiko diringkas + ditahan untuk konfirmasi (lalu dieksekusi setelah disetujui).
"""
from __future__ import annotations

import json

from sadar.config import AppConfig
from sadar.core.ports import BackendSpec
from sadar.main import build_sadar
from sadar.text_chat import drain


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


def test_text_drain_prints_reply(tmp_path, capsys):
    eng = build_sadar(
        AppConfig(store={"root": str(tmp_path / "m")}, loop={"tick_interval_s": 0.0}),
        backend=Scripted([json.dumps({"reasoning": "x", "reply": "Halo Pak Syam.", "action": None})]))
    eng.perceiver.push("halo")
    eng.tick()
    drain(eng, set(), None)
    assert "Halo Pak Syam." in capsys.readouterr().out


def test_text_risky_command_summarized_and_gated(tmp_path, capsys):
    (tmp_path / "data").mkdir()
    cfg = AppConfig(store={"root": str(tmp_path / "m")},
                    shell={"workdir": str(tmp_path), "full_access": True},
                    loop={"tick_interval_s": 0.0})
    eng = build_sadar(cfg, cli=True, backend=Scripted([json.dumps(
        {"reasoning": "hapus", "reply": "", "action": {"tool": "shell", "args": {"cmd": "rm -rf data"}}})]))
    eng.perceiver.push("hapus folder data")
    eng.tick()
    pending = drain(eng, set(), None)
    out = capsys.readouterr().out
    assert pending is not None                          # ada konfirmasi tertunda
    assert "Apakah Pak Syams setuju" in out             # konfirmasi yang jelas
    assert "menghapus" in out                           # RINGKASAN (bukan hanya perintah mentah)
    assert (tmp_path / "data").exists()                 # belum dieksekusi sebelum disetujui
    eng.confirm(pending)
    assert not (tmp_path / "data").exists()             # setelah disetujui → terhapus


def test_text_safe_command_runs_directly(tmp_path, capsys):
    cfg = AppConfig(store={"root": str(tmp_path / "m")},
                    shell={"workdir": str(tmp_path), "full_access": True},
                    loop={"tick_interval_s": 0.0})
    eng = build_sadar(cfg, cli=True, backend=Scripted([json.dumps(
        {"reasoning": "cek", "reply": "Ini hasilnya.", "action": {"tool": "shell", "args": {"cmd": "echo sadar-teks"}}})]))
    eng.perceiver.push("jalankan echo")
    eng.tick()
    drain(eng, set(), None)
    out = capsys.readouterr().out
    assert "sadar-teks" in out and "Ini hasilnya." in out   # keluaran + jawaban tampil, tanpa konfirmasi
