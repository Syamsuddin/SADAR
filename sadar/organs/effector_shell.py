"""ShellEffector — tangan CLI: menjalankan perintah di macOS, DIGERBANG KETAT oleh KODE.

Dipasang sebagai adapter (nol perubahan core/). Aman-berlapis, semua deterministik:
  - tool 'shell'        : perintah BACA-saja (allowlist), reversible → jalan langsung.
  - tool 'shell_write'  : perintah MUTASI (allowlist), reversible=False → WAJIB konfirmasi HITL
                          (lewat handshake konstitusi yang sudah ada).
Pertahanan (semua di KODE, bukan ditimbang LLM):
  - kapabilitas wajib (shell.read / shell.write) — gerbang konstitusi.
  - allowlist nama-perintah (basename murni; jalur biner eksplisit DITOLAK → cegah biner palsu).
  - TANPA shell=True + tolak metakarakter (; | & < > $ ( ) backtick newline) → cegah injeksi/pipe/redirect.
  - timeout, batas panjang output.
Hasil perintah kembali jadi persepsi (anti fire-and-forget). Perintah destruktif berat
(rm, dd, kill, sudo, …) SENGAJA tak masuk allowlist default — tambah sendiri bila benar perlu.
"""
from __future__ import annotations

import os
import re
import shlex
import subprocess

from sadar.core.ports import ActionResult, EffectorSpec, ToolSpec

# metakarakter shell yang menandakan butuh shell (injeksi/pipe/redirect/substitusi) → DITOLAK.
_META = re.compile(r"[;&|<>$()\n`]")

# allowlist BAWAAN — konservatif, baca-saja & aman. SENGAJA tanpa:
#   - find  : punya -delete/-exec (bisa hapus/jalankan tanpa metakarakter) → footgun.
#   - env   : membocorkan variabel lingkungan (mis. ANTHROPIC_API_KEY).
_DEFAULT_READ = {
    "ls", "pwd", "cat", "head", "tail", "echo", "date", "whoami", "uname", "hostname",
    "df", "du", "wc", "grep", "which", "ps", "sw_vers", "uptime", "cal", "stat", "file",
}
# mutasi yang relatif terbatas — TETAP butuh konfirmasi manusia (HITL). rm/dd/sudo TIDAK di sini.
_DEFAULT_WRITE = {"mkdir", "touch", "cp", "mv"}

# Peta kata-kerja untuk RINGKASAN perintah (diucapkan saat konfirmasi). Deterministik, KODE.
_VERB = {
    "rm": "menghapus", "rmdir": "menghapus folder", "shred": "menghancurkan berkas",
    "mkdir": "membuat folder", "touch": "membuat berkas", "mv": "memindahkan/mengganti nama",
    "cp": "menyalin", "ln": "membuat tautan", "tee": "menulis ke berkas", "ditto": "menyalin",
    "chmod": "mengubah izin", "chown": "mengubah kepemilikan", "chgrp": "mengubah grup",
    "chflags": "mengubah atribut", "truncate": "memangkas berkas",
    "kill": "menghentikan proses", "killall": "menghentikan proses", "pkill": "menghentikan proses",
    "dd": "menulis langsung ke disk", "mkfs": "memformat disk", "fdisk": "mengubah partisi",
    "diskutil": "mengelola disk", "mount": "memasang volume", "umount": "melepas volume",
    "curl": "mengunduh dari internet", "wget": "mengunduh dari internet",
    "scp": "menyalin lewat jaringan", "rsync": "menyinkronkan berkas", "ssh": "menyambung ke mesin lain",
    "brew": "mengelola paket", "pip": "memasang paket", "pip3": "memasang paket",
    "npm": "mengelola paket", "yarn": "mengelola paket", "gem": "memasang paket",
    "apt": "mengelola paket", "apt-get": "mengelola paket", "git": "menjalankan perintah git",
    "launchctl": "mengelola layanan", "systemctl": "mengelola layanan",
    "shutdown": "mematikan sistem", "reboot": "menyalakan ulang sistem", "crontab": "mengubah jadwal tugas",
    "python": "menjalankan skrip Python", "python3": "menjalankan skrip Python",
    "node": "menjalankan skrip", "ruby": "menjalankan skrip", "perl": "menjalankan skrip",
    "bash": "menjalankan skrip", "zsh": "menjalankan skrip", "sh": "menjalankan skrip",
    "osascript": "menjalankan skrip sistem", "find": "mencari/mengolah berkas", "open": "membuka berkas/aplikasi",
}
_FILE_OPS = {"rm", "rmdir", "shred", "mkdir", "touch", "mv", "cp", "ln", "tee", "ditto",
             "chmod", "chown", "chgrp", "chflags", "truncate", "curl", "wget", "scp", "open"}


def summarize_command(cmd: str, max_target: int = 40) -> str:
    """Ringkasan SINGKAT & jujur sebuah perintah CLI — untuk DIUCAPKAN saat konfirmasi.
    Deterministik (KODE), tak menafsir via LLM. Perintah MENTAH tetap tampil di layar untuk verifikasi."""
    s = (cmd or "").strip()
    if not s:
        return "perintah kosong"
    toks = s.split()
    if _META.search(s):                      # pipa/redirect/chain → ringkas generik (jangan eja)
        head = os.path.basename(toks[0]) if toks else "perintah"
        return f"perintah gabungan diawali '{head}' (memakai pipa atau redirect)"
    try:
        parts = shlex.split(s)
    except ValueError:
        parts = toks
    admin = ""
    i = 0
    while i < len(parts) and os.path.basename(parts[i]) in ("sudo", "doas"):
        admin = "sebagai admin, "
        i += 1
    while i < len(parts) and ("=" in parts[i]) and not parts[i].startswith("-"):
        i += 1                               # lewati env VAR=val
    rest = parts[i:]
    if not rest:
        return (admin + "menjalankan perintah").strip()
    binary = os.path.basename(rest[0])
    verb = _VERB.get(binary, f"menjalankan {binary}")
    targets = [p for p in rest[1:] if not p.startswith("-")]
    if targets and binary in _FILE_OPS:
        tgt = targets[-1]
        if len(tgt) > max_target:
            tgt = "…" + tgt[-max_target:]
        extra = f" dan {len(targets) - 1} lainnya" if len(targets) > 1 else ""
        return f"{admin}{verb} '{tgt}'{extra}"
    return f"{admin}{verb}".strip()


class ShellEffector:
    def __init__(self, workdir: str | None = None, timeout: float = 20.0, max_output: int = 4000,
                 read_allow: set[str] | None = None, write_allow: set[str] | None = None,
                 full_access: bool = False, sandbox: bool = False, sandbox_image: str = "alpine"):
        self.workdir = workdir or os.path.expanduser("~")
        self.timeout = timeout
        self.max_output = max_output
        self.read_allow = set(read_allow) if read_allow is not None else set(_DEFAULT_READ)
        self.write_allow = set(write_allow) if write_allow is not None else set(_DEFAULT_WRITE)
        # MODE AKSES-PENUH: satu tool 'shell' menerima perintah APA PUN (termasuk pipe/redirect).
        # Penyaringan risiko (berisiko→konfirmasi) dilakukan KONSTITUSI (KODE), bukan di sini.
        self.full_access = full_access
        # SANDBOX (4.1): jalankan di kontainer Docker terisolasi (tanpa jaringan, batas memori/CPU,
        # hanya workdir ter-mount) → DEFENSE-IN-DEPTH di atas gerbang risiko KODE & HITL (bukan pengganti).
        self.sandbox = sandbox
        self.sandbox_image = sandbox_image

    def _docker_argv(self, cmd: str) -> list[str]:
        """Bangun perintah `docker run` terisolasi: tanpa jaringan, batas sumber daya, workdir ter-mount."""
        return [
            "docker", "run", "--rm", "--network", "none",
            "--memory", "256m", "--cpus", "1", "--pids-limit", "256",
            "-v", f"{self.workdir}:/work", "-w", "/work",
            self.sandbox_image, "sh", "-c", cmd,
        ]

    def list_tools(self) -> list[ToolSpec]:
        if self.full_access:
            # reversible=True → tak auto-HITL lewat irreversibility; gerbang risiko (hitl_risky_command)
            # di konstitusi yang menahan perintah berisiko. Butuh shell.read+shell.write.
            return [ToolSpec(name="shell", reversible=True, side_effect="external",
                             required_caps=["shell.read", "shell.write"],
                             usage='args {"cmd": "perintah CLI apa pun (pipe/redirect boleh); '
                                   'yang berisiko otomatis minta konfirmasi manusia"}')]
        return [
            ToolSpec(name="shell", reversible=True, side_effect="read", required_caps=["shell.read"],
                     usage=f'args {{"cmd": "perintah baca"}} — allowlist: {", ".join(sorted(self.read_allow))}'),
            ToolSpec(name="shell_write", reversible=False, side_effect="destructive",
                     required_caps=["shell.write"],   # reversible=False → gerbang HITL menahan
                     usage=f'args {{"cmd": "perintah ubah"}} — allowlist: {", ".join(sorted(self.write_allow))}'),
        ]

    def act(self, tool: str, args: dict) -> ActionResult:
        cb = args.get("_caused_by", [])
        if tool not in ("shell", "shell_write"):
            return ActionResult(tool=tool, ok=False, output=f"tool tak dikenal: {tool}", caused_by=cb)
        cmd = str(args.get("cmd", "")).strip()
        if not cmd:
            return ActionResult(tool=tool, ok=False, output="perintah kosong", caused_by=cb)
        if self.full_access:
            return self._act_full(cmd, cb)
        if _META.search(cmd):
            return ActionResult(tool=tool, ok=False,
                                output="ditolak: metakarakter shell terlarang (pipe/redirect/;/&/$/(/backtick)",
                                caused_by=cb)
        try:
            parts = shlex.split(cmd)
        except ValueError as e:
            return ActionResult(tool=tool, ok=False, output=f"perintah tak terurai: {e}", caused_by=cb)
        if not parts:
            return ActionResult(tool=tool, ok=False, output="perintah kosong", caused_by=cb)
        binary = parts[0]
        if "/" in binary:
            return ActionResult(tool=tool, ok=False,
                                output="ditolak: jalur biner eksplisit tak diizinkan; pakai nama perintah",
                                caused_by=cb)
        allow = self.read_allow if tool == "shell" else self.write_allow
        if binary not in allow:
            return ActionResult(tool=tool, ok=False,
                                output=f"ditolak: '{binary}' tak ada di allowlist {tool}", caused_by=cb)
        try:
            proc = subprocess.run(parts, cwd=self.workdir, capture_output=True, text=True,
                                  timeout=self.timeout)
        except subprocess.TimeoutExpired:
            return ActionResult(tool=tool, ok=False, output=f"timeout >{self.timeout}s", caused_by=cb)
        except Exception as e:  # noqa: BLE001
            return ActionResult(tool=tool, ok=False, output=f"galat: {e}", caused_by=cb)
        out = (proc.stdout + proc.stderr).strip()
        if len(out) > self.max_output:
            out = out[: self.max_output] + f"\n…[dipotong, total {len(out)} char]"
        body = out if out else f"(exit {proc.returncode})"
        return ActionResult(tool=tool, ok=(proc.returncode == 0),
                            output=f"$ {cmd}\n{body}", caused_by=cb)

    def _act_full(self, cmd: str, cb: list) -> ActionResult:
        """Akses-penuh: jalankan perintah APA PUN via shell (dukung pipe/redirect/~/var).
        Penyaringan risiko SUDAH dilakukan gerbang konstitusi (perintah berisiko butuh konfirmasi
        manusia) SEBELUM sampai di sini. Tetap dibatasi timeout & panjang output."""
        try:
            if self.sandbox:
                proc = subprocess.run(self._docker_argv(cmd), capture_output=True,
                                      text=True, timeout=self.timeout)   # terisolasi (Docker)
            else:
                proc = subprocess.run(cmd, shell=True, cwd=self.workdir, capture_output=True,
                                      text=True, timeout=self.timeout,
                                      executable=os.environ.get("SHELL", "/bin/zsh"))
        except subprocess.TimeoutExpired:
            return ActionResult(tool="shell", ok=False, output=f"timeout >{self.timeout}s", caused_by=cb)
        except Exception as e:  # noqa: BLE001
            return ActionResult(tool="shell", ok=False, output=f"galat: {e}", caused_by=cb)
        out = (proc.stdout + proc.stderr).strip()
        if len(out) > self.max_output:
            out = out[: self.max_output] + f"\n…[dipotong, total {len(out)} char]"
        body = out if out else f"(exit {proc.returncode})"
        return ActionResult(tool="shell", ok=(proc.returncode == 0),
                            output=f"$ {cmd}\n{body}", caused_by=cb)

    def spec(self) -> EffectorSpec:
        return EffectorSpec(name="shell-cli", provenance="local", trust=1.0)
