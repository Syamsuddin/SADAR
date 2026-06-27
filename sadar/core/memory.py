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
        self._summary_buf: list[tuple[str, str]] = []   # (id, content) menunggu diringkas (2.2)

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
    def consolidate(self, d: Dosir, backend=None) -> None:
        """Item salient di workspace → tulis ke store (jika belum ada). Bila summarize_every>0 &
        ada backend, tiap N item terkonsolidasi diringkas jadi SATU MemoryItem turunan (2.2)."""
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
                self._summary_buf.append((rep.id, rep.content))   # antre untuk ringkasan
        self._maybe_summarize(backend)

    def _maybe_summarize(self, backend) -> None:
        """Ringkas batch item dingin → MemoryItem turunan (tag 'summary', caused_by=sumber).
        Ringkasan = KONTEN turunan (LLM boleh; bukan gerbang keselamatan). Sumber MENTAH tetap
        tersimpan (markdown=kebenaran) → tetap dapat di-audit & di-reindex (Aturan Kardinal #2/#3)."""
        every = getattr(self.cfg, "summarize_every", 0) if self.cfg else 0
        if not every or backend is None or len(self._summary_buf) < every:
            return
        batch = self._summary_buf[:every]
        self._summary_buf = self._summary_buf[every:]
        ids = [i for i, _ in batch]
        body = "\n".join(f"- {c}" for _, c in batch)
        try:
            raw = backend.complete(
                "Kamu meringkas catatan menjadi satu paragraf padat & faktual. "
                "JANGAN menambah informasi yang tak ada di catatan; jangan mengarang.",
                "Ringkas poin-poin berikut jadi satu paragraf intisari:\n" + body, tier="sys2")
        except Exception:  # noqa: BLE001 — kegagalan S2 tak boleh menjatuhkan konsolidasi
            self._summary_buf = batch + self._summary_buf   # kembalikan batch; coba lagi nanti
            return
        text = (raw or "").strip()
        if not text:
            return
        self.store.write(MemoryItem(
            content=f"[ringkasan] {text}", tags=["summary"], caused_by=ids,
            importance=0.7, vec=self.embed(text)))

    # ---------- model pengguna (2.3): fakta tertambat tentang yang dilayani ----------
    def user_facts(self, limit: int = 6) -> list[MemoryItem]:
        """MemoryItem ber-tag 'user_model' (terbaru dulu) — disuntik ke konteks agar personal.
        Tertambat: tiap fakta punya caused_by ke observasi sumber (lihat UserModelEffector)."""
        items = []
        for cid in self.store.list():
            it = self.store.read(cid)
            if it and "user_model" in it.tags:
                items.append(it)
        items.sort(key=lambda i: i.created, reverse=True)
        return items[:limit]

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
