"""Metabolisme — Mesin A (denyut metabolik). Berjalan tiap tik TANPA LLM.

Inilah sumber 'dorongan dari dalam' yang membedakan SADAR dari sistem reaktif.
Gerbang warrants_deliberation() menentukan kapan membangunkan System-2 yang mahal.
"""
from __future__ import annotations

from sadar.core.dosir import Dosir, Drive


def _clamp(x: float, lo: float = 0.0, hi: float = 1.0) -> float:
    return max(lo, min(hi, x))


class Metabolism:
    def __init__(self, cfg):
        self.cfg = cfg

    def regulate(self, d: Dosir) -> None:
        """Homeostasis: energi meluruh tiap tik."""
        d.viability.energy = _clamp(d.viability.energy - self.cfg.energy_decay_per_tick)

    def appraise(self, d: Dosir) -> list[Drive]:
        """Sinyal internal → valensi → drive. Sumber motivasi intrinsik."""
        drives: list[Drive] = []
        if d.pending_count > 0:
            drives.append(Drive(
                name="answer_pending",
                valence=-0.4,
                urgency=_clamp(0.2 * d.pending_count),
            ))
        idle = d.tick_count - d.last_meaningful_action_tick
        if idle > self.cfg.idle_threshold:
            drives.append(Drive(name="seek_meaning", valence=-0.2, urgency=0.3))
        if d.viability.energy < self.cfg.low_energy:
            drives.append(Drive(name="conserve", valence=-0.6, urgency=0.7))
        if d.coherence < self.cfg.low_coherence:
            drives.append(Drive(name="consolidate", valence=-0.3, urgency=0.4))
        # METAKOGNISI: self-model kurang yakin → dorongan mengurangi ketidakpastian.
        if d.confidence < self.cfg.low_confidence:
            drives.append(Drive(name="reduce_uncertainty", valence=-0.3,
                                urgency=_clamp(0.6 * (1.0 - d.confidence))))
        return drives

    def warrants_deliberation(self, d: Dosir) -> bool:
        """Gerbang metabolik: bangunkan S2 (mahal) hanya saat layak.
        Drive cukup mendesak ATAU ada kebaruan ATAU surprise (metakognisi) tinggi."""
        peak = max((dr.urgency for dr in d.drives), default=0.0)
        return (peak >= self.cfg.deliberation_threshold or d.novel_percept
                or d.surprise >= self.cfg.surprise_threshold)
