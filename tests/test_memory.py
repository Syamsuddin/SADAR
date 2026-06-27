"""Memori — Markdown=kebenaran tunggal, indeks vektor=TURUNAN.

Menguji: (a) 'diri' bertahan lintas-restart (kebenaran di .md), (b) indeks rusak
→ reindex() dari .md memulihkan tanpa kehilangan data, (c) RAM pra-sadar
(working_memory) TRANSIEN — engine baru mulai kosong walau store berisi.
"""
from __future__ import annotations

from sadar.core.ports import MemoryItem
from sadar.organs.memory_markdown import MarkdownVectorStore
from tests.mocks import SilentBackend, build_test_sadar


# --- persistensi lintas-restart: kebenaran ada di .md --------------------------
def test_persistence_across_restart(tmp_path):
    root = str(tmp_path / "mem")
    s1 = MarkdownVectorStore(root)
    item = MemoryItem(content="rapat penting jam 9 pagi")
    s1.write(item)
    s1.close()                                  # "mati"

    s2 = MarkdownVectorStore(root)              # "hidup lagi" — proses baru, root sama
    got = s2.read(item.id)

    assert got is not None
    assert "rapat penting" in got.content       # kebenaran selamat di Markdown


# --- indeks turunan rusak → reindex memulihkan, NOL kehilangan -----------------
def test_reindex_no_loss(tmp_path):
    s = MarkdownVectorStore(str(tmp_path / "mem"))
    s.write(MemoryItem(content="alpha membahas kucing oranye"))
    s.write(MemoryItem(content="beta membahas anjing hitam"))
    q = s.embed("kucing")

    assert s.search(q, 5), "indeks awal seharusnya mengembalikan kandidat"

    s._db.execute("DELETE FROM vec")            # RUSAKKAN indeks turunan
    s._db.commit()
    assert s.search(q, 5) == []                 # indeks kosong → tak ada kandidat

    s.reindex()                                  # bangun ulang dari .md (kebenaran)

    assert s.search(q, 5), "reindex gagal memulihkan dari Markdown (ada kehilangan)"


# --- working_memory (pra-sadar) TRANSIEN: diri ada di store, bukan RAM ---------
def test_working_memory_transient(tmp_path):
    # isi store lebih dulu
    s = MarkdownVectorStore(str(tmp_path / "mem"))
    s.write(MemoryItem(content="kenangan lama yang tersimpan"))
    s.close()

    # engine baru di atas store yang SAMA
    eng = build_test_sadar(tmp_path, SilentBackend())

    assert eng.d.working_memory.warm == []      # RAM hangat mulai kosong
    assert eng.d.workspace.items == []          # sorotan kesadaran mulai kosong
    # ...meski store BERISI — yang persisten ada di store, dipanggil lewat recall saat perlu
    assert eng.memory.store.list(), "store seharusnya tetap berisi kenangan lama"


# --- dorman != tersembunyi: yang tersimpan dapat dipanggil kembali jujur -------
def test_dormant_is_recallable_not_hidden(tmp_path):
    eng = build_test_sadar(tmp_path, SilentBackend())
    eng.memory.store.write(MemoryItem(content="paspor ada di laci atas meja kerja"))

    hits = eng.memory.recall("di mana paspor", k=3)

    assert any("paspor" in h.content for h in hits)   # tak ada gudang represi
