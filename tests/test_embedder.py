"""Embedder 'auto' (semantik bila tersedia, hashing bila tidak) — berdaulat & tanpa unduhan paksa.

Membuktikan: default config = 'auto'; 'auto' resolve ke embedder yang berfungsi (di env tanpa
sentence-transformers → hashing, tak crash); pilihan eksplisit tetap dihormati; ganti embedder +
reindex tetap nol-kehilangan (markdown=kebenaran).
"""
from __future__ import annotations

import importlib.util

from sadar.config import StoreConfig
from sadar.core.ports import MemoryItem
from sadar.organs.memory_markdown import (HashingEmbedder, MarkdownVectorStore, get_embedder)

_ST_AVAILABLE = importlib.util.find_spec("sentence_transformers") is not None


def test_default_embedder_is_auto():
    assert StoreConfig().embedder == "auto"


def test_auto_resolves_to_working_embedder():
    e = get_embedder("auto")
    v = e("halo dunia")
    assert isinstance(v, list) and len(v) > 0 and hasattr(e, "name")
    if not _ST_AVAILABLE:
        assert e.name == "hashing"        # tanpa ST → fallback berdaulat (tak crash, tak unduh)


def test_explicit_choices_respected():
    assert get_embedder("hashing").name == "hashing"
    assert isinstance(get_embedder("local-hash"), HashingEmbedder)


def test_switch_embedder_reindex_lossless(tmp_path):
    # tulis dgn hashing → ganti instance (simulasi ganti embedder) → reindex dari .md → konten utuh
    st = MarkdownVectorStore(str(tmp_path), embedder=get_embedder("hashing"))
    st.write(MemoryItem(content="paspor di laci atas", tags=["note"]))
    st2 = MarkdownVectorStore(str(tmp_path), embedder=get_embedder("hashing"))
    st2.reindex()
    got = [st2.read(c).content for c in st2.list()]
    assert "paspor di laci atas" in got       # md=kebenaran → nol-kehilangan lintas reindex
