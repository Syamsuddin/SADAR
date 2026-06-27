"""MemoryEngine — logika kognitif memori. 'Store menyimpan, Engine berpikir.'

Membungkus MemoryStore (port). search() store hanya kandidat KASAR; peringkat di sini.
Dinamika aktivasi: TURUN = decay berbobot-kepentingan; NAIK = spreading activation.
Disiplin: dorman != tersembunyi (tak ada gudang represi).
"""
from __future__ import annotations

from sadar.core.dosir import Dosir, Representation
from sadar.core.mathx import cosine
from sadar.core.ports import MemoryItem, MemoryStore


def _to_repr(item: MemoryItem) -> Representation:
    return Representation(
        id=item.id,
        content=item.content,
        source="memory",
        vec=item.vec,
        trust=1.0,
        caused_by=item.caused_by,
        activation=0.5,
    )


class MemoryEngine:
    def __init__(self, store: MemoryStore, embed, cfg=None):
        self.store = store
        self.embed = embed
        self.cfg = cfg

    # ---------- recall ----------
    def recall(self, query: str, k: int = 5) -> list[Representation]:
        qvec = self.embed(query)
        cand_ids = self.store.search(qvec, k * 3)        # kandidat KASAR
        scored: list[tuple[float, MemoryItem]] = []
        for cid in cand_ids:
            item = self.store.read(cid)
            if item is None:
                continue
            sim = cosine(qvec, item.vec or self.embed(item.content))
            score = sim * (0.5 + 0.5 * item.importance)   # PERINGKAT di sini
            scored.append((score, item))
        scored.sort(key=lambda t: t[0], reverse=True)
        return [_to_repr(it) for _, it in scored[:k]]

    # ---------- consolidate ----------
    def consolidate(self, d: Dosir) -> None:
        """Item salient di workspace → tulis ke store (jika belum ada)."""
        existing = set(self.store.list())
        for rep in d.workspace.items:
            # lewati percept ephemeral (mis. detak jam) — jangan cemari kebenaran persisten.
            if (rep.source in ("perception", "thought", "action_result")
                    and rep.activation >= 0.5 and not rep.ephemeral):
                if rep.id in existing:
                    continue
                self.store.write(MemoryItem(
                    id=rep.id,
                    content=rep.content,
                    tags=[rep.source],
                    caused_by=rep.caused_by,
                    importance=min(1.0, 0.4 + rep.activation * 0.4),
                    vec=rep.vec or self.embed(rep.content),
                ))

    # ---------- dinamika aktivasi ----------
    def decay_and_spread(self, d: Dosir) -> None:
        rate = self.cfg.activation_decay if self.cfg else 0.85
        warm = self.cfg.warm_threshold if self.cfg else 0.25
        hot = self.cfg.hot_threshold if self.cfg else 0.66
        # 0) RAM hangat lama IKUT mendingin; yang di bawah ambang dilepas → jadi dorman (di store),
        #    bukan beku selamanya (perbaikan warm-memory-frozen).
        for rep in d.working_memory.warm:
            rep.activation = max(0.0, rep.activation * rate)
        d.working_memory.warm = [r for r in d.working_memory.warm if r.activation >= warm]
        # 1) TURUN: decay aktivasi workspace
        for rep in d.workspace.items:
            rep.activation = max(0.0, rep.activation * rate)
        # 2) NAIK: spreading activation NYATA — isi PANAS menularkan sebagian aktivasi ke tetangga
        #    kausal (caused_by) yang masih di workspace (asosiatif). Kini nama 'spread' jujur.
        by_id = {r.id: r for r in d.workspace.items}
        boost: dict[str, float] = {}
        for rep in d.workspace.items:
            if rep.activation >= hot:
                for cid in rep.caused_by:
                    if cid in by_id:
                        boost[cid] = boost.get(cid, 0.0) + 0.1 * rep.activation
        for rid, b in boost.items():
            by_id[rid].activation = min(1.0, by_id[rid].activation + b)
        # 3) demosi: workspace -> working_memory bila mendingin
        keep, demote = [], []
        for rep in d.workspace.items:
            (keep if rep.activation >= hot else demote).append(rep)
        d.workspace.items = keep
        for rep in demote:
            if rep.activation >= warm:
                d.working_memory.warm.append(rep)
            # < warm: jadi dorman (di store via consolidate) — TIDAK disembunyikan.
        if d.workspace.focus and d.workspace.focus not in {r.id for r in d.workspace.items}:
            d.workspace.focus = None
