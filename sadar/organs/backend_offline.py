"""OfflineBackend — stand-in System-2 untuk demo tanpa API key.

BUKAN pengganti LLM sungguhan; ia deterministik dan dangkal, hanya agar lingkaran
terlihat berputar saat ANTHROPIC_API_KEY tak ada. spec() tetap 'local' & trust tinggi
(karena tak ada premis yang keluar). Untuk deliberasi sebenarnya, pakai ClaudeBackend.

Mengeluarkan KONTRAK TERSTRUKTUR (JSON) yang sama seperti yang diharapkan dari S2
sungguhan (lihat core/protocol.py) — jadi jalur parse terstruktur ikut teruji end-to-end.
"""
from __future__ import annotations

import json
import re

from sadar.core.ports import BackendSpec, ReasonTier


class OfflineBackend:
    """Implements ModelBackend. Jika konteks memuat pesan pengguna, usulkan note_create."""

    def complete(self, system: str, prompt: str, *, tier: ReasonTier = "sys2") -> str:
        # konteks dirakit sebagai dialog (B): ambil giliran "Pengguna:" TERAKHIR.
        users = re.findall(r"^\s*Pengguna:\s*(.+)$", prompt, re.M) or re.findall(r"pesan pengguna:\s*(.+)", prompt)
        if users:
            text = users[-1].strip().strip('"')
            return json.dumps({
                "reasoning": "Aku mencatat permintaan ini agar tidak terlupa.",
                "reply": f"Baik, sudah kucatat: {text}",
                "action": {"tool": "note_create", "args": {"text": text}},
            }, ensure_ascii=False)
        return json.dumps({
            "reasoning": "Aku mengamati keadaan; belum ada yang menuntut tindakan.",
            "action": None,
        }, ensure_ascii=False)

    def spec(self) -> BackendSpec:
        return BackendSpec(name="offline-stub", provenance="local", trust=0.9,
                           tiers=["sys2"], leaves_premises=False)

    def available(self) -> bool:
        return True
