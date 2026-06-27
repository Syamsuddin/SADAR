"""Ringkasan aksi untuk konfirmasi HITL (diucapkan/ditampilkan). PRESENTASI, bukan keputusan.

Dipakai voice_chat & text_chat agar pesan konfirmasi konsisten & ringkas (tak membaca perintah
mentah panjang). Vonis tetap di KODE (gerbang konstitusi); ini hanya merangkai kalimatnya.
"""
from __future__ import annotations

import re

from sadar.organs.effector_shell import summarize_command

_VERB = {
    "skill_create": "menyimpan skill",
    "skill_delete": "menghapus skill",
    "note_delete": "menghapus catatan",
    "note_update": "memperbarui catatan",
    "tool_enable": "menyalakan-ulang tool",
}

_PENDING_RE = re.compile(r"aksi '([^']*)'(?::\s*(.+?))?\s+—")


def describe_for_confirm(tool: str, detail: str) -> str:
    """Frasa ringkas & jujur untuk satu aksi tertunda."""
    if tool in ("shell", "shell_write"):
        return summarize_command(detail)
    if tool in _VERB:
        return f"{_VERB[tool]} '{detail}'" if detail else _VERB[tool]
    return f"aksi {tool} '{detail}'" if detail else f"aksi {tool}"


def confirm_summary(thought_content: str) -> str:
    """Ekstrak (tool, detail) dari pesan '[KONFIRMASI DIBUTUHKAN …]' → frasa konfirmasi."""
    m = _PENDING_RE.search(thought_content)
    if not m:
        return "perintah ini"
    return describe_for_confirm(m.group(1), (m.group(2) or "").strip())
