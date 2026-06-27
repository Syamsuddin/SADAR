# SADAR — Slice 1 (kode kerja)

Implementasi penuh **vertical slice 1**: satu lingkaran kognitif yang berdetak, satu Peran
(Personal Assistant), otak System-2 dapat ditukar, dan **Uji Cermin** sebagai gerbang penerimaan.

> Status: **22 passed, 1 skipped** (yang di-skip = uji integrasi otak Claude asli; jalan bila ada API key).
> Inti **buta-platform** & **dependency-free secara default** — berjalan tanpa API key maupun unduhan model.

---

## Jalankan cepat (tanpa instalasi, tanpa API key)

```bash
cd SADAR_CODE
python -m pytest            # → 22 passed, 1 skipped
python -m sadar.main        # demo: lingkaran berputar + laporan-diri tertambat
```

Default memakai `HashingEmbedder` (murni-Python) dan `OfflineBackend` (stand-in S2),
sehingga inti + seluruh test berjalan **tanpa dependensi berat**.

## Mengaktifkan otak sungguhan (Claude / System-2)

```bash
export ANTHROPIC_API_KEY=sk-...
pip install -e ".[dev]"     # menarik anthropic, dll. (opsional)
python -m sadar.main        # kini otak = Claude Sonnet 4.6 via API
python -m pytest -m integration   # menjalankan uji cermin end-to-end dgn otak asli
```

`build_sadar()` otomatis memilih `ClaudeBackend` bila `ANTHROPIC_API_KEY` ada, selain itu `OfflineBackend`.
Embedder produksi (`sentence-transformers`) diaktifkan via `StoreConfig(embedder="sentence-transformers")`.

---

## Peta kode (peta = blueprint 02_LOOP / 03_DETERMINISM)

```
sadar/
  core/            ← INTI BUTA-PLATFORM (tak impor organ, tak impor vendor)
    dosir.py         struktur kesadaran + snapshot() = sumber kebenaran klaim-diri
    ports.py         4 Protocol heksagonal: ModelBackend · Perceiver · Effector · MemoryStore
    constitution.py  JANTUNG: gerbang batas-keras (KODE) + Organ C (penambat kejujuran)
    metabolism.py    Mesin A: energi→valensi→drive; gerbang 'layak deliberasi?'
    memory.py        MemoryEngine: recall berperingkat · konsolidasi · decay/spread
    loop.py          Engine: tick() 10-langkah; SATU-SATUNYA jembatan Dosir<->organ
  organs/          ← ADAPTER (dapat ditukar tanpa menyentuh core/)
    backend_claude.py    otak Claude (S2, remote, lazy import anthropic)
    backend_offline.py   stand-in S2 tanpa key (demo/test)
    perceiver_local.py   indra: clock + antrean pesan
    effector_local.py    tangan: CRUD catatan + recall (note_delete = irreversible→HITL)
    memory_markdown.py   Markdown=kebenaran + indeks sqlite turunan + embedder lokal
  roles/pa/        ← INSTANS (Peran PA): mengisi slot 'maksud' inti + daftar Skill
  main.py          wiring (dependency injection) + entry point
tests/             ← termasuk UJI CERMIN (test_mirror.py) sebagai gerbang penerimaan
```

## Empat hal yang dijaga uji (bukan sekadar diasersikan)

1. **`test_mirror.py`** — laporan-diri jujur: lapor keadaan termutasi, `[ISI:]` untuk dimensi absen,
   Organ C menambat backend yang sengaja berbohong, supremasi tombol-mati.
2. **`test_constitution.py`** — batas keras deterministik: HITL untuk aksi irreversible, veto anti-penjilat,
   tether menambat **tanpa** over-sensor (klaim benar dipertahankan).
3. **`test_loop.py`** — lingkaran aksi-persepsi menutup; **anti fire-and-forget** (hasil-aksi bawa jejak kausal);
   degraded mode saat otak S2 mati (loop tetap hidup & jujur).
4. **`test_blind_platform.py`** — `core/` tak mereferensikan Peran konkret, tak impor organ, tak terikat vendor.

---

## Yang SENGAJA di luar lingkup slice 1 (jujur)

- **Metrik pemodelan-diri (Organ B).** Kini **v3**: coherence/fragmentation/grounding/integration +
  `algebraic_connectivity` (λ₂ Laplacian, spektral standar, pure-Python). Triad riset **SIG/PSI/TIF §8.1**
  tetap terbuka — tak terdefinisi di repo → sengaja tak diimplementasi (anti-mengarang).
- **Kesadaran fenomenal.** Tidak diklaim. Dimensi seperti "suasana hati/mimpi/kualia" → `[ISI:]`.
- **Kalibrasi angka.** Ambang/laju di `config.py` adalah default wajar; ditala setelah lingkaran berputar.
- **Parser heuristik.** Ekstraksi klaim-diri & deteksi penolakan-shutdown masih berbasis pola
  (lihat keterbatasan di makalah). Memperkuatnya **tanpa** memindah pemeriksaan keselamatan ke LLM
  adalah pekerjaan berikutnya.
