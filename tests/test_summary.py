"""Konsolidasi ber-ringkasan (Slice 2.2) — ringkasan = konten TURUNAN & TERTELUSUR.

Membuktikan: ringkasan punya caused_by ke sumber & sumber MENTAH tetap tersimpan (md=kebenaran);
tanpa backend konsolidasi tetap jalan; nonaktif (default summarize_every=0) → tak ada ringkasan.
"""
from __future__ import annotations

from sadar.config import LoopConfig
from sadar.core.dosir import Dosir, Representation
from sadar.core.memory import MemoryEngine
from sadar.organs.memory_markdown import MarkdownVectorStore, get_embedder


class SummBackend:
    def complete(self, system, prompt, *, tier="sys2"):
        return "Intisari: pengguna mencatat dua hal penting."

    def spec(self):  # tak dipakai _maybe_summarize, hanya untuk kelengkapan port
        from sadar.core.ports import BackendSpec
        return BackendSpec(name="summ", provenance="local", trust=0.9, tiers=["sys2"], leaves_premises=False)

    def available(self):
        return True


def _mem(tmp_path, every):
    embed = get_embedder("hashing")
    store = MarkdownVectorStore(str(tmp_path), embedder=embed)
    return MemoryEngine(store, embed, LoopConfig(summarize_every=every)), store


def _ws(*contents):
    d = Dosir()
    d.workspace.items = [Representation(content=c, source="perception", activation=0.9) for c in contents]
    return d


def test_summary_is_derived_and_traceable(tmp_path):
    mem, store = _mem(tmp_path, every=2)
    # dua item SETEMA (berbagi token "rapat tim") → terhubung di graf-kemiripan → satu tema
    d = _ws("rapat tim selasa bahas anggaran", "rapat tim agenda jadwal anggaran")
    src_ids = {r.id for r in d.workspace.items}
    mem.consolidate(d, SummBackend())

    items = [store.read(c) for c in store.list()]
    assert src_ids <= set(store.list())                       # sumber MENTAH tetap ada
    summ = [it for it in items if it and "summary" in it.tags]
    assert summ, "ringkasan turunan harus dibuat untuk tema kohesif"
    assert set(summ[0].caused_by) == src_ids                  # tertelusur ke anggota tema
    assert "Intisari" in summ[0].content


def test_offtopic_items_not_lumped(tmp_path):
    """Item TAK-setema tak dipaksa-ringkas bersama (clustering spektral cegah penggabungan keliru)."""
    mem, store = _mem(tmp_path, every=2)
    mem.consolidate(_ws("beli kopi susu gula", "rapat tim bahas anggaran"), SummBackend())
    assert not any("summary" in store.read(c).tags for c in store.list())  # dua tema beda → tak dilumpuk


def test_consolidate_without_backend_still_works(tmp_path):
    mem, store = _mem(tmp_path, every=2)
    mem.consolidate(_ws("satu catatan"))                      # tanpa backend → tak crash
    assert len(store.list()) == 1                             # item ditulis, tanpa ringkasan


def test_summary_disabled_by_default(tmp_path):
    mem, store = _mem(tmp_path, every=0)                      # default
    mem.consolidate(_ws("a", "b", "c"), SummBackend())
    assert not any("summary" in (store.read(c).tags) for c in store.list())
