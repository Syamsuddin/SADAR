"""MarkdownVectorStore — Markdown = kebenaran tunggal; indeks vektor = TURUNAN.

Implementasi slice 1 yang berdaulat & dependency-free secara default:
- kebenaran: file .md + frontmatter (dapat dibaca/diff/di-git)
- indeks: sqlite3 stdlib menyimpan (id, vec_json); pencarian cosine murni-Python
- embedder: HashingEmbedder murni-Python (default); sentence-transformers (opsional, lazy)

reindex() membangun ulang SELURUH indeks dari .md → indeks rusak = regen, NOL kehilangan.
Catatan produksi: indeks dapat diganti sqlite-vec; embedder diganti sentence-transformers,
tanpa mengubah tanda tangan port (search() tetap kandidat kasar).
"""
from __future__ import annotations

import hashlib
import math
import os
import re
import sqlite3
from pathlib import Path

from sadar.core.mathx import cosine
from sadar.core.ports import MemoryItem, StoreSpec

# id catatan yang sah = slug aman (uuid4 hex memenuhi ini). Menutup path traversal di _path().
_ID_RE = re.compile(r"[A-Za-z0-9_-]+\Z")


# ============ embedder lokal ============
class HashingEmbedder:
    """Bag-of-hashed-tokens → vektor ter-normalisasi. Deterministik, tanpa dependensi.
    Menangkap tumpang-tindih LEKSIKAL (cukup untuk recall slice 1; bukan makna semantik penuh)."""

    name = "hashing"

    def __init__(self, dim: int = 256):
        self.dim = dim

    def __call__(self, text: str) -> list[float]:
        vec = [0.0] * self.dim
        for tok in re.findall(r"\w+", text.lower()):
            h = int(hashlib.md5(tok.encode()).hexdigest(), 16)
            vec[h % self.dim] += 1.0
        norm = math.sqrt(sum(x * x for x in vec))
        return [x / norm for x in vec] if norm else vec


class SentenceTransformerEmbedder:
    """Embedder SEMANTIK produksi (lazy import). Tetap LOKAL (di perangkat) — tak membocorkan premis."""

    def __init__(self, model: str = "all-MiniLM-L6-v2"):
        from sentence_transformers import SentenceTransformer  # lazy
        self._m = SentenceTransformer(model)
        self.name = f"sentence-transformers:{model}"

    def __call__(self, text: str) -> list[float]:
        return self._m.encode(text, normalize_embeddings=True).tolist()


def get_embedder(name: str = "auto"):
    """Pilih embedder. 'auto' = SEMANTIK (sentence-transformers, lokal) bila terpasang & dapat dimuat,
    jatuh ke HASHING (berdaulat, tanpa unduhan) bila tidak — sepola selektor backend. Eksplisit
    'hashing'/'sentence-transformers' memaksa pilihan. Markdown=kebenaran → ganti embedder + reindex()
    aman (vektor=indeks turunan; mathx.cosine tahan beda-dimensi)."""
    if name in ("hashing", "local-hash"):
        return HashingEmbedder()
    if name in ("sentence-transformers", "st"):
        return SentenceTransformerEmbedder()
    if name == "auto":
        try:
            return SentenceTransformerEmbedder()       # semantik bila tersedia (mungkin unduh sekali)
        except Exception:  # noqa: BLE001 — ImportError / gagal muat/unduh → fallback berdaulat
            return HashingEmbedder()
    raise ValueError(f"embedder tak dikenal: {name}")


# ============ frontmatter minimal (stdlib, tanpa PyYAML) ============
def _dump_md(item: MemoryItem) -> str:
    fm = [
        "---",
        f"id: {item.id}",
        f"created: {item.created}",
        f"tags: {', '.join(item.tags)}",
        f"caused_by: {', '.join(item.caused_by)}",
        f"importance: {item.importance}",
        "---",
    ]
    return "\n".join(fm) + "\n" + item.content + "\n"


def _flt(v: object, default: float) -> float:
    """Parse float toleran — frontmatter cacat tak boleh meng-crash pembacaan memori."""
    try:
        return float(v)  # type: ignore[arg-type]
    except (TypeError, ValueError):
        return default


def _parse_md(text: str, fallback_id: str) -> MemoryItem:
    meta: dict = {}
    body = text
    m = re.match(r"^---\n(.*?)\n---\n(.*)$", text, re.DOTALL)
    if m:
        for line in m.group(1).splitlines():
            if ":" in line:
                k, v = line.split(":", 1)
                meta[k.strip()] = v.strip()
        body = m.group(2)

    def _list(s: str) -> list[str]:
        return [x.strip() for x in s.split(",") if x.strip()]

    return MemoryItem(
        id=fallback_id,                       # nama file = kebenaran (cegah spoof id di frontmatter)
        content=body.rstrip("\n"),
        tags=_list(meta.get("tags", "")),
        caused_by=_list(meta.get("caused_by", "")),
        importance=_flt(meta.get("importance"), 0.5),
        created=_flt(meta.get("created"), 0.0),
    )


# ============ store ============
class MarkdownVectorStore:
    """Implements MemoryStore. Markdown=kebenaran, sqlite=indeks turunan."""

    def __init__(self, root: str = "memory", embedder=None):
        self.root = Path(root)
        self.root.mkdir(parents=True, exist_ok=True)
        self.embed = embedder or HashingEmbedder()
        self._db = sqlite3.connect(str(self.root / ".index.sqlite"))
        self._db.execute("CREATE TABLE IF NOT EXISTS vec (id TEXT PRIMARY KEY, v TEXT)")
        self._db.commit()

    # --- kebenaran (Markdown) ---
    def _path(self, id: str) -> Path:
        # SANITASI satu chokepoint: id catatan bisa berasal dari args LLM (read/update/delete).
        # Tolak apa pun selain slug aman → cegah path traversal ('../', '/', absolut, spasi).
        if not _ID_RE.fullmatch(id or ""):
            raise ValueError(f"id catatan tak aman: {id!r}")
        return self.root / f"{id}.md"

    def write(self, item: MemoryItem) -> None:
        item.vec = item.vec or self.embed(item.content)
        self._path(item.id).write_text(_dump_md(item), encoding="utf-8")     # .md = kebenaran
        self._upsert_index(item.id, item.vec)                                # indeks = turunan (SINKRON)

    def read(self, id: str) -> MemoryItem | None:
        p = self._path(id)
        if not p.exists():
            return None
        item = _parse_md(p.read_text(encoding="utf-8"), id)
        if item.vec is None:
            item.vec = self._get_vec(id) or self.embed(item.content)
        return item

    def delete(self, id: str) -> None:
        p = self._path(id)
        if p.exists():
            p.unlink()
        self._db.execute("DELETE FROM vec WHERE id=?", (id,))
        self._db.commit()

    def list(self) -> list[str]:
        return [p.stem for p in self.root.glob("*.md")]

    def neighbors(self, id: str) -> list[str]:
        item = self.read(id)
        if item is None:
            return []
        out = list(item.caused_by)
        for other in self.list():                  # siapa yang menyebut id ini
            if other == id:
                continue
            oi = self.read(other)
            if oi and id in oi.caused_by:
                out.append(other)
        return out

    # --- indeks (turunan) ---
    def _upsert_index(self, id: str, vec: list[float]) -> None:
        import json
        self._db.execute("INSERT OR REPLACE INTO vec (id, v) VALUES (?, ?)", (id, json.dumps(vec)))
        self._db.commit()

    def _get_vec(self, id: str) -> list[float] | None:
        import json
        row = self._db.execute("SELECT v FROM vec WHERE id=?", (id,)).fetchone()
        return json.loads(row[0]) if row else None

    def search(self, query_vec: list[float], k: int = 8) -> list[str]:
        import json
        scored: list[tuple[float, str]] = []
        for i, v in self._db.execute("SELECT id, v FROM vec").fetchall():
            try:
                scored.append((cosine(query_vec, json.loads(v)), i))
            except (json.JSONDecodeError, TypeError):
                continue   # baris indeks rusak dilewati (fail-soft); .md tetap kebenaran
        scored.sort(key=lambda t: t[0], reverse=True)
        return [i for _, i in scored[:k]]

    def reindex(self) -> None:
        """Bangun ulang SELURUH indeks dari file .md. File rusak dilewati (fail-soft) → indeks
        rusak = regen dari Markdown (kebenaran) dengan kehilangan minimal, bukan crash."""
        self._db.execute("DELETE FROM vec")
        self._db.commit()
        for id in self.list():
            try:
                item = _parse_md(self._path(id).read_text(encoding="utf-8"), id)
                self._upsert_index(id, item.vec or self.embed(item.content))
            except Exception:
                continue

    def spec(self) -> StoreSpec:
        return StoreSpec(name="markdown+sqlite-index", provenance="local",
                         trust=1.0, readable=True, leaves_premises=False)

    def close(self) -> None:
        self._db.close()
