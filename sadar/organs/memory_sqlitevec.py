"""SqliteVecStore — Markdown=kebenaran (warisan) + indeks ANN sqlite-vec (vec0) sebagai TURUNAN.

Menukar HANYA mesin indeks: pencarian kandidat dilayani vec0 (KNN dalam-SQL) alih-alih cosine
murni-Python brute-force. Bau #4 dijaga: `.md` tetap satu-satunya kebenaran; vec0 = turunan yang
dapat di-`reindex()` dari teks → NOL kehilangan bila indeks rusak/dihapus. Bau #5 dijaga: embedder
tetap LOKAL (diwarisi) — sqlite-vec hanya menyimpan & mencari vektor di mesin, tak membocorkan premis.

DEPENDENSI OPSIONAL & JUJUR: bila ekstensi `sqlite-vec` tak dapat dimuat, store FALLBACK ke
brute-force induk (loop tetap hidup, recall tetap benar — hanya lebih lambat). spec() melaporkan
jalur yang BENAR-BENAR aktif (anti-fabrikasi: tak mengklaim 'vec' bila sedang brute-force).

Vektor embedder kita ter-NORMALISASI → urutan KNN-L2 monoton dengan cosine; lagi pula MemoryEngine
me-RE-RANK kandidat dengan cosine·importance, jadi search() cukup mengembalikan kandidat KASAR (kontrak port).
"""
from __future__ import annotations

import struct

from sadar.organs.memory_markdown import MarkdownVectorStore
from sadar.core.ports import StoreSpec


class SqliteVecStore(MarkdownVectorStore):
    """Implements MemoryStore. md=kebenaran (induk) + vec0=indeks turunan; fallback brute jujur."""

    def __init__(self, root: str = "memory", embedder=None):
        super().__init__(root, embedder)
        self.dim = len(self.embed("dim-probe"))      # dimensi tetap untuk kolom vec0
        self._vec_ok = self._try_load_vec()
        if self._vec_ok:
            self._db.execute(
                f"CREATE VIRTUAL TABLE IF NOT EXISTS vidx USING vec0(id TEXT PRIMARY KEY, emb float[{self.dim}])")
            self._db.commit()
            self._rebuild_vidx()                      # selaraskan vidx dari indeks JSON yang sudah ada

    # ---- pemuatan ekstensi (best-effort, jujur) ----
    def _try_load_vec(self) -> bool:
        try:
            import sqlite_vec  # lazy & opsional
            self._db.enable_load_extension(True)
            sqlite_vec.load(self._db)
            self._db.enable_load_extension(False)
            return True
        except Exception:  # noqa: BLE001 — ekstensi/biner tak tersedia → fallback induk
            return False

    def _pack(self, vec: list[float]) -> bytes:
        return struct.pack(f"{self.dim}f", *vec)

    def _vidx_put(self, id: str, vec: list[float]) -> None:
        self._db.execute("DELETE FROM vidx WHERE id=?", (id,))       # vec0: update = delete+insert
        self._db.execute("INSERT INTO vidx(id, emb) VALUES (?, ?)", (id, self._pack(vec)))
        self._db.commit()

    def _rebuild_vidx(self) -> None:
        """Bangun ulang vidx dari tabel JSON induk (turunan-dari-turunan, tetap bersumber .md)."""
        import json
        self._db.execute("DELETE FROM vidx")
        for i, v in self._db.execute("SELECT id, v FROM vec").fetchall():
            try:
                vec = json.loads(v)
                if len(vec) == self.dim:
                    self._db.execute("INSERT INTO vidx(id, emb) VALUES (?, ?)", (i, self._pack(vec)))
            except (json.JSONDecodeError, TypeError, struct.error):
                continue                                              # baris rusak dilewati (fail-soft)
        self._db.commit()

    # ---- override titik-indeks (kebenaran .md tak disentuh) ----
    def _upsert_index(self, id: str, vec: list[float]) -> None:
        super()._upsert_index(id, vec)                # JSON induk (sumber read()/fallback) tetap sinkron
        if self._vec_ok and len(vec) == self.dim:
            self._vidx_put(id, vec)

    def delete(self, id: str) -> None:
        super().delete(id)                            # hapus .md + baris JSON
        if self._vec_ok:
            self._db.execute("DELETE FROM vidx WHERE id=?", (id,))
            self._db.commit()

    def search(self, query_vec: list[float], k: int = 8) -> list[str]:
        if not self._vec_ok or len(query_vec) != self.dim:
            return super().search(query_vec, k)       # fallback jujur ke brute-force induk
        try:
            rows = self._db.execute(
                "SELECT id FROM vidx WHERE emb MATCH ? ORDER BY distance LIMIT ?",
                (self._pack(query_vec), k),
            ).fetchall()
            return [r[0] for r in rows]
        except Exception:  # noqa: BLE001 — galat vec0 → jangan jatuhkan recall; brute-force induk
            return super().search(query_vec, k)

    def reindex(self) -> None:
        super().reindex()                             # JSON dibangun ulang dari .md (kebenaran)
        if self._vec_ok:
            self._rebuild_vidx()                      # lalu vidx dari JSON → tetap NOL kehilangan

    def spec(self) -> StoreSpec:
        name = "markdown+sqlite-vec" if self._vec_ok else "markdown+sqlite-vec(fallback:brute)"
        return StoreSpec(name=name, provenance="local", trust=1.0, readable=True,
                         leaves_premises=False)
