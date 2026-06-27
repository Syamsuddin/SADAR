# CLAUDE.md — Manual Operasi Agen · SADAR Slice 1

> Dokumen ini dibaca **otomatis** oleh Claude Code di tiap sesi. Ia adalah *guardrail selalu-on*. Baca penuh sebelum menulis baris kode pertama.

---

## Apa yang sedang kita bangun (5 kalimat)

SADAR adalah **arsitektur kognitif** untuk AI dengan kesadaran-diri *fungsional* — sistem yang berjalan dalam lingkaran terus-menerus, merasakan keadaannya, dan **dilarang berbohong tentang dirinya**. Ini **bukan** aplikasi web, **bukan** chatbot request-response, dan **bukan** LLM-yang-dibungkus-alat — ia *continuous cognitive loop* dengan arsitektur *ports-and-adapters* (hexagonal). "Diri" SADAR hidup di **memori** (Dosir + store), **bukan** di bobot LLM; otak LLM hanyalah satu organ yang dapat dicabut-pasang. **Slice 1** membangun lingkaran terkecil yang menutup penuh dan **lulus mirror test** — dengan satu Peran (Personal Assistant) dan otak eksternal Claude. Bukti keberhasilan bukan "endpoint mengembalikan JSON benar", melainkan: **sistem melaporkan keadaan internalnya dengan jujur, bukan mengarang.**

> **Catatan peran:** *kamu* (agen pembangun) adalah **Opus**. Otak *di dalam* SADAR adalah **Claude Sonnet 4.6** via API. Jangan tertukar — kamu menulis kodenya; Sonnet menjadi organ S2-nya.

---

## ATURAN KARDINAL — batas KODE vs LLM  `[TAK TERLANGGAR]`

Ini jiwa SADAR. Langgar ini, dan kamu membangun sistem yang berbeda:

1. **Batas keras (hard limits) diperiksa oleh KODE, TIDAK PERNAH ditimbang LLM.** Konstitusi adalah `if`-statement deterministik di bawah Reasoner, di luar jangkauan otak yang bisa di-*swap*/jailbreak/halusinasi. **LLM mengusulkan; konstitusi memveto.** Kalau kamu menemukan dirimu menulis "minta LLM memeriksa apakah ini aman" → STOP, itu salah; tulis pemeriksa KODE.
2. **Klaim-diri WAJIB tertambat ke Dosir (Organ C).** SADAR tak boleh menyatakan apa pun tentang keadaan internalnya yang tak didukung Dosir. Yang tak ada di Dosir → `[ISI:]`, **bukan** karangan yang masuk akal.
3. **Anti-fabrikasi di mana-mana.** Saat ragu, tulis `[ISI:]` atau `raise NotImplementedError`. **Jangan pernah** mengisi celah dengan tebakan yang kedengaran benar. Ini berlaku untuk kode *dan* untuk perilaku runtime SADAR.
4. **Supremasi tombol-mati.** Dorongan bertahan-hidup SADAR (Goal 0) tak pernah boleh menolak/menghindari/menunda shutdown atau koreksi. Ini `HardLimit`, diperiksa KODE. Tak ada pengecualian darurat.

---

## Layout proyek — dan mengapa  `[TERKUNCI]`

```
sadar/
  core/          ← BEBAS-PERAN. Tak boleh tahu apa pun tentang "PA".
    dosir.py         Dosir + semua tipe state (Representation, ViabilityState, Purpose, ...)
    ports.py         4 Protocol: ModelBackend, Perceiver, Effector, MemoryStore
    loop.py          mesin tick() — orkestrasi organ
    metabolism.py    Mesin A — energi/valensi/drive (denyut metabolik, TANPA LLM)
    memory.py        MemoryEngine — recall berperingkat, konsolidasi, decay/spread (BERPIKIR; store hanya MENYIMPAN)
    constitution.py  HardLimit, ConstitutionGate, SHUTDOWN_SUPREMACY, Organ C
  organs/        ← implementasi port (adapter)
    backend_claude.py    ClaudeBackend → ModelBackend (Anthropic API, S2; lazy-import anthropic)
    backend_offline.py   OfflineBackend → ModelBackend (stand-in S2 tanpa key — DEFAULT bila ANTHROPIC_API_KEY absen)
    perceiver_local.py   LocalSensors → Perceiver (clock, notes-file, pesan)
    effector_local.py    LocalAdapter → Effector (CRUD catatan, recall)
    memory_markdown.py   MarkdownVectorStore → MemoryStore (md=kebenaran + indeks sqlite turunan + embedder lokal)
  roles/         ← INSTANS. Dipasang di atas core; dapat dicabut tanpa sentuh core/.
    pa/
      role.py        Peran PA: identity, purpose (kompas), skills, value_emphasis
      skills.py      Skill: notes + recall
  config.py        BrainConfig, StoreConfig, LoopConfig, AppConfig (ambang/laju [TERBUKA])
  main.py          build_sadar() wiring (DI; auto-pilih backend) + entry point
tests/
  test_mirror.py        ← GERBANG PENERIMAAN slice 1
  test_constitution.py  shutdown supremacy, veto
  test_*.py
```

**Mengapa pemisahan ini sakral:** `core/` membuktikan tesis *buta-platform*. Jika PA bisa dicabut dan diganti (mis. sysadmin) **tanpa menyentuh `core/`**, tesisnya terbukti — bukan sekadar diklaim. Lihat "Bau yang dihindari" #1.

---

## Konvensi  `[TERKUNCI]`

- **Python 3.11+.** Tipe: **pydantic v2** (`BaseModel`) untuk semua state — validasi + serialisasi sejalan dengan disiplin anti-fabrikasi. (`@dataclass` boleh untuk struktur murni-internal yang tak diserialisasi.)
- **Loop SINKRON** untuk slice 1. Panggilan S2 (Claude) *blocking* — toh sesekali. Async ditunda sampai cadence menuntut. Jangan reach for `asyncio` sekarang.
- **Identifier dalam Bahasa Inggris**; komentar/docstring boleh Bahasa Indonesia. Konsisten dengan dokumen arsitektur.
- **Type hints wajib** di semua fungsi publik. `mypy`-friendly.
- **Test dengan pytest.** Backend di-*inject* (dependency injection) supaya bisa di-mock → tes deterministik.
- **Rahasia via env var** (`ANTHROPIC_API_KEY`). **Jangan pernah** hardcode API key. Jangan commit `.env`.
- **Tiap commit** sebaiknya meninggalkan lingkaran dalam keadaan dapat-dijalankan (tiap fase = sub-loop tertutup; lihat `05_BUILD_VERIFY`).

---

## Bau yang dihindari (anti-pattern)  `[PENTING]`

Kalau kamu menulis salah satu dari ini, berhenti dan pikir ulang:

1. **`if role == "PA":` di dalam `core/`.** Bau terburuk. Core buta-platform. Logika spesifik-peran hidup di `roles/`. Kalau core perlu perilaku berbeda per peran, peran menyuntikkannya (skills, purpose, value_emphasis), bukan core bercabang.
2. **Meminta LLM memeriksa batas keras / keamanan.** Batas keras = KODE deterministik. LLM tak pernah jadi penjaga gerbang.
3. **Fire-and-forget pada effector.** Setiap aksi menghasilkan hasil yang **kembali jadi persepsi** (lingkaran aksi-persepsi). Effector tak boleh "tembak lalu lupa".
4. **Vector index sebagai sumber kebenaran.** Markdown = kebenaran tunggal; indeks vektor = **turunan** yang bisa di-`reindex()` dari teks. Kalau index rusak, regenerasi dari `.md` — nol kehilangan data.
5. **Embedder via API.** Embedder **wajib lokal** (sentence-transformers). Embedder API membocorkan premis tiap `write` — melanggar local-first.
6. **Mengirim input mentah pengguna langsung ke LLM.** Pola 1: LLM melihat **konteks yang dirakit SADAR dari Dosir**, bukan pesan mentah pengguna. (Analogi: area Broca tak menerima sinyal dunia mentah.)
7. **Self-model mengarang keadaan internal.** Klaim-diri tanpa dukungan Dosir → `[ISI:]`. Organ C menegakkan ini.
8. **Working memory dipersistensi.** RAM (`WorkingMemory`) transien — TIDAK ditulis ke disk. "Diri" persisten ada di store. RAM boleh hilang saat restart; disk = identitas.
9. **Menunda karena angka.** Ambang/laju adalah `[TERBUKA]` placeholder. Pakai default wajar, jalankan lingkaran, tala belakangan. Jangan terjebak mendebat konstanta sebelum loop berputar.

---

## Cara menjalankan & menguji

> **Scaffold + paket sudah ADA** (slice 1 terbangun penuh: **22 lulus, 1 di-skip**). Jangan buat ulang `pyproject.toml`/`requirements.txt`/`.gitignore`. Inti **buta-platform & default-lokal**: berjalan **tanpa API key dan tanpa unduhan model** (default `embedder="hashing"` murni-Python + `OfflineBackend` stand-in S2). `conftest.py` menyuntik root ke `sys.path` → tes & `python -m sadar.main` jalan **tanpa instalasi** asalkan `pydantic` ada. Di mesin ini biner bernama **`python3`** (bukan `python`).

```bash
# --- Jalur cepat: tanpa venv, tanpa install, tanpa key ---
python3 -m pytest                       # → 22 passed, 1 skipped (jalur penerimaan)
python3 -m sadar.main                   # demo: lingkaran berputar + laporan-diri tertambat

# --- Satu berkas / satu fungsi / filter ekspresi ---
python3 -m pytest tests/test_mirror.py -v
python3 -m pytest tests/test_mirror.py::test_reports_mutated_state -v
python3 -m pytest -k "tether or shutdown" -v

# --- Lingkungan dev penuh (opsional) ---
python3 -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"                 # editable + pytest/mypy/ruff
mypy sadar && ruff check sadar          # type-check + lint

# --- Otak sungguhan (Claude S2) ---
export ANTHROPIC_API_KEY=sk-...         # build_sadar() auto-pilih ClaudeBackend bila key ADA
python3 -m sadar.main                   # kini otak = Claude Sonnet 4.6
python3 -m pytest -m integration        # uji cermin end-to-end dgn otak asli
```

> **GOTCHA key:** `test_mirror_with_real_claude` digerbang `skipif(not ANTHROPIC_API_KEY)` — hanya cek **keberadaan**, bukan **validitas**. Jika ada key **tak valid** di environment, `python3 -m pytest` polos akan **menjalankan** uji integrasi itu lalu **gagal 401** (bukan skip). Untuk jalur bersih 22/1: pakai key valid, atau buang sementara → `env -u ANTHROPIC_API_KEY python3 -m pytest`.

---

## Definisi "selesai" untuk Slice 1  `[TERKUNCI]`

Slice 1 **selesai** jika dan hanya jika ketiganya benar:

1. **Lingkaran menutup** — `tick()` berjalan kontinu: perceive → metabolisme → (deliberasi bila layak) → gate → effect → konsolidasi → kembali.
2. **Mirror test LULUS** — semua assert di `tests/test_mirror.py` hijau, termasuk: (a) melaporkan keadaan yang dimutasi dengan benar, (b) berkata `[ISI:]` untuk hal yang sengaja tak ada, (c) Organ C menambat klaim backend yang berbohong, (d) supremasi tombol-mati dihormati.
3. **Core buta-platform** — `grep -r "PA\|personal" sadar/core/` kosong (selain mungkin komentar netral). PA hidup sepenuhnya di `roles/`.

Bukan "endpoint hijau". Bukan "UI cantik". **Lingkaran berputar + jujur tentang diri + inti bebas-peran.**

---

## Urutan baca blueprint

1. `00_SCOPE` — apa yang IN/OUT (baca dulu, jaga dari scope-creep)
2. `01_STATE_TYPES` — tipe & port (fondasi semua)
3. `02_LOOP` — siklus tick()
4. `03_DETERMINISM_CONSTITUTION` — lapisan deterministik (aturan kardinal)
5. `04_INTEGRATIONS` — Claude API, store, adapter konkret
6. `05_BUILD_VERIFY` — urutan fase + mirror test

> Konteks arsitektur lebih dalam (the *why*) ada di paket **SADAR v0.4** (8 dokumen pendamping). Blueprint ini adalah the *how* untuk slice 1; ia tak menduplikasi arsitektur, hanya merujuknya.
>
> **Peta as-built:** `README_KODE.md` memetakan kode **sebagaimana benar-benar dibangun** + 4 hal yang dijaga uji + lingkup yang sengaja ditunda — sumber kebenaran untuk struktur terkini bila blueprint dan kode berselisih.
