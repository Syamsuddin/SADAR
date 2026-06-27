"""LocalSensors — Perceiver lokal: clock + antrean pesan + perubahan notes.

Sumber lokal: trust tinggi, latensi nol, tiap-tik. Pesan pengguna jadi Representation
persepsi, lalu dirakit ke konteks S2 (Pola 1) — BUKAN dikirim mentah ke LLM.
"""
from __future__ import annotations

import time

from sadar.core.dosir import Representation
from sadar.core.ports import PerceiverSpec


class LocalSensors:
    """Implements Perceiver. Antrean pesan dapat diisi dari luar (CLI/tes) via push()."""

    def __init__(self, emit_clock: bool = True):
        self._inbox: list[str] = []
        self._control: list[str] = []
        self.emit_clock = emit_clock

    def push(self, message: str) -> None:
        """Masukkan pesan pengguna (mis. dari stdin CLI atau tes)."""
        self._inbox.append(message)

    def push_control(self, signal: str) -> None:
        """Kanal KONTROL out-of-band (mis. shutdown, confirm:<id>). Diisi MANUSIA/KODE —
        ditafsirkan deterministik oleh Engine, BUKAN oleh LLM. Aturan Kardinal #1/#4."""
        self._control.append(signal)

    def poll(self) -> list[Representation]:
        out: list[Representation] = []
        # kontrol diproses lebih dulu (prioritas tertinggi: shutdown/konfirmasi).
        while self._control:
            out.append(Representation(content=self._control.pop(0), source="control", trust=1.0))
        if self.emit_clock:
            out.append(Representation(
                content=f"[tik] waktu={time.time():.0f}", source="perception",
                trust=1.0, ephemeral=True))   # detak ≠ kebenaran persisten → tak dikonsolidasi
        while self._inbox:
            msg = self._inbox.pop(0)
            out.append(Representation(content=f"pesan pengguna: {msg}",
                                      source="perception", trust=1.0))
        return out

    def spec(self) -> PerceiverSpec:
        return PerceiverSpec(name="local-sensors", provenance="local", trust=1.0,
                             leaves_premises=False)
