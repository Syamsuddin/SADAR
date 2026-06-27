"""CompositePerceiver — gabung beberapa Perceiver di balik SATU port (cermin CompositeEffector).

Memungkinkan banyak indra (lokal + kanal: Telegram, dsb.) hidup berdampingan tanpa menyentuh inti
(Engine tetap memanggil satu .poll()). spec() JUJUR: trust = minimum, leaves_premises = ada-satu-pun,
provenance = remote bila ada indra remote → Organ C tetap melihat masukan paling tak-tepercaya.
"""
from __future__ import annotations

from sadar.core.ports import PerceiverSpec


class CompositePerceiver:
    """Implements Perceiver. Menyatukan persepsi dari semua sub-Perceiver (urut argumen)."""

    def __init__(self, *perceivers):
        self._perceivers = [p for p in perceivers if p is not None]

    def poll(self):
        out = []
        for p in self._perceivers:
            out.extend(p.poll())
        return out

    def spec(self) -> PerceiverSpec:
        specs = [p.spec() for p in self._perceivers]
        if not specs:
            return PerceiverSpec(name="composite()", provenance="local", trust=1.0,
                                 leaves_premises=False)
        return PerceiverSpec(
            name="composite(" + "+".join(s.name for s in specs) + ")",
            provenance="remote" if any(s.provenance == "remote" for s in specs) else "local",
            trust=min(s.trust for s in specs),                 # masukan paling tak-tepercaya yang menentukan
            leaves_premises=any(s.leaves_premises for s in specs),
        )
