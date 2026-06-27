"""SqliteVecStore — indeks ANN lokal (sqlite-vec) di atas md=kebenaran.

Membuktikan: search() vec0 mengembalikan kandidat relevan & SETARA brute-force induk (urutan top
sama pada vektor ternormalisasi); reindex() tetap NOL kehilangan dari .md; delete() menyapu indeks;
md tetap satu-satunya kebenaran (hapus DB indeks → reindex pulih); spec() jujur 'local'; integrasi
MemoryEngine.recall() bekerja. Embedder tetap LOKAL (Bau #5). Dilewati bila ekstensi tak terpasang.
"""
from __future__ import annotations

import pytest

sqlite_vec = pytest.importorskip("sqlite_vec")     # skip jujur bila ekstensi tak ada (suite tetap hijau)

from sadar.core.memory import MemoryEngine                       # noqa: E402
from sadar.organs.memory_markdown import MarkdownVectorStore, get_embedder  # noqa: E402
from sadar.organs.memory_sqlitevec import SqliteVecStore          # noqa: E402
from sadar.core.ports import MemoryItem                           # noqa: E402


def _seed(store):
    store.write(MemoryItem(id="a1", content="jadwal menyiram tanaman tiap pagi"))
    store.write(MemoryItem(id="b2", content="nomor telepon dokter gigi"))
    store.write(MemoryItem(id="c3", content="ide proyek arsitektur kognitif SADAR"))


def test_extension_actually_loaded(tmp_path):
    store = SqliteVecStore(root=str(tmp_path), embedder=get_embedder("hashing"))
    assert store._vec_ok is True            # ekstensi vec0 benar-benar dimuat (bukan fallback)
    store.close()


def test_search_returns_relevant_candidate(tmp_path):
    store = SqliteVecStore(root=str(tmp_path), embedder=get_embedder("hashing"))
    _seed(store)
    ids = store.search(store.embed("kapan menyiram tanaman"), k=3)
    assert "a1" in ids                              # kandidat relevan tertangkap vec0


def test_topcandidate_matches_bruteforce(tmp_path):
    """vec0 (L2 atas vektor ternormalisasi) memberi kandidat-puncak SAMA dengan brute-force cosine induk."""
    vec_store = SqliteVecStore(root=str(tmp_path / "vec"), embedder=get_embedder("hashing"))
    brute = MarkdownVectorStore(root=str(tmp_path / "brute"), embedder=get_embedder("hashing"))
    for s in (vec_store, brute):
        _seed(s)
    q = vec_store.embed("telepon dokter")
    assert vec_store.search(q, k=1)[0] == brute.search(q, k=1)[0] == "b2"


def test_reindex_lossless_from_markdown(tmp_path):
    store = SqliteVecStore(root=str(tmp_path), embedder=get_embedder("hashing"))
    _seed(store)
    # buang SELURUH indeks turunan (JSON + vec0), seolah indeks rusak
    store._db.execute("DELETE FROM vec"); store._db.execute("DELETE FROM vidx"); store._db.commit()
    assert store.search(store.embed("menyiram tanaman"), k=3) == []   # indeks kosong
    store.reindex()                                                    # regen dari .md (kebenaran)
    assert "a1" in store.search(store.embed("menyiram tanaman"), k=3)  # pulih NOL kehilangan


def test_delete_sweeps_index(tmp_path):
    store = SqliteVecStore(root=str(tmp_path), embedder=get_embedder("hashing"))
    _seed(store)
    store.delete("a1")
    assert "a1" not in store.search(store.embed("menyiram tanaman"), k=3)
    assert store.read("a1") is None                 # .md juga terhapus (kebenaran)


def test_spec_is_local_and_names_vec(tmp_path):
    store = SqliteVecStore(root=str(tmp_path), embedder=get_embedder("hashing"))
    sp = store.spec()
    assert sp.provenance == "local" and sp.leaves_premises is False
    assert "sqlite-vec" in sp.name and "fallback" not in sp.name


def test_memory_engine_recall_with_vec(tmp_path):
    store = SqliteVecStore(root=str(tmp_path), embedder=get_embedder("hashing"))
    _seed(store)
    eng = MemoryEngine(store, store.embed)
    hits = eng.recall("proyek SADAR", k=2)
    assert any("SADAR" in h.content for h in hits)   # recall berperingkat tetap bekerja
