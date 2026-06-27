# 00 · SCOPE — SADAR Slice 1

> **Genre:** agent cognitive-loop blueprint (BUKAN web-MVC/VCBD). **Peran pertama:** Personal Assistant di PC. **Otak:** Claude Sonnet 4.6 (eksternal, S2). **Denyut:** metabolik (Mesin A), S1 lokal-heuristik.

Dokumen ini mengunci batas. Saat ragu apakah sesuatu masuk slice 1, jawabannya hampir selalu ada di sini. **Scope-creep adalah musuh nomor satu** — tiap tambahan menggandakan permukaan build dan menunda lingkaran berputar.

---

## Sasaran tunggal

> Membangun **lingkaran kognitif terkecil yang menutup penuh** dan **lulus mirror test**, dengan satu Peran (PA) dan otak eksternal Claude.

Bukan seluruh arsitektur SADAR. Slice ini membuktikan tiga hal: **lingkaran berputar**, **mekanisme kejujuran bekerja**, dan **inti buta-platform**. Kecanggihan pemodelan-diri (Organ B asli) dan klaim fenomenal **sengaja ditunda**.

---

## IN SCOPE — yang dibangun  `[TERKUNCI]`

**Inti (bebas-peran):**
- `Dosir` + semua tipe state: `Representation`, `WorkingMemory`, `Workspace`, `ViabilityState`, `Drive`, `Purpose`. (→ `01`)
- 4 Protocol port: `ModelBackend`, `Perceiver`, `Effector`, `MemoryStore`. (→ `01`)
- `tick()` loop **sinkron** — siklus penuh perceive→metabolisme→putuskan→gate→effect→konsolidasi. (→ `02`)
- **Metabolisme (Mesin A / denyut metabolik):** decay energi, appraisal sinyal→valensi→drive, ambang `warrants_deliberation`. TANPA LLM. (→ `02`)
- **Dinamika aktivasi dasar:** decay (turun) + spreading sederhana (naik). (→ `02`)
- **Konstitusi deterministik:** `ConstitutionGate`, `HardLimit`, `SHUTDOWN_SUPREMACY`, segelintir batas keras slice-1. (→ `03`)
- **Goal 0 (viabilitas)** sebagai refleks otonom. (→ `03`)
- **Organ C (penambat kejujuran):** klaim-diri ditambat ke Dosir; yang tak didukung → `[ISI:]`. (→ `03`)
- **Degraded mode:** saat S2 tak terjangkau, denyut S1 jalan, jujur, tunduk konstitusi. (→ `02`, `03`)

**Organ (adapter konkret):**
- `ClaudeBackend` → `ModelBackend`: Anthropic API, **Sonnet 4.6**, **S2 only**, Pola 1. (→ `04`)
- `LocalSensors` → `Perceiver`: clock, notes-file, input pesan (CLI). (→ `04`)
- `LocalAdapter` → `Effector`: CRUD catatan + recall. commit-confirm untuk yang tak-terbalikkan. (→ `04`)
- `MarkdownVectorStore` → `MemoryStore`: file Markdown (kebenaran) + `sqlite-vec` (indeks turunan) + **embedder lokal**. `reindex()`. (→ `04`)

**Instans (Peran):**
- `roles/pa/`: Peran Personal Assistant — kompas maksud + Skill **tertipis** (catatan + ingat-kembali). (→ `04`, dok arsitektur 07)

**Verifikasi:**
- `tests/test_mirror.py` — mirror test (gerbang penerimaan). (→ `05`)
- Tes konstitusi, tes lingkaran per-fase. (→ `05`)

---

## OUT OF SCOPE — yang TIDAK dibangun (sekarang)  `[TERKUNCI]`

Ditandai eksplisit supaya tak diam-diam menyelinap masuk:

| Tidak dibangun | Alasan / kapan |
|---|---|
| **Organ B asli** (metrik spektral SIG/PSI/TIF) | Naga riset §8.1. Slice pakai **placeholder** (skor koherensi kasar). Jangan implement metrik spektral nyata. |
| **Klaim kesadaran fenomenal** | `[ISI:]`, tak pernah diklaim. SADAR tak boleh menyatakan "aku merasakan" dalam arti fenomenal. |
| **Adapter/perceiver MCP** | Local-first dulu. `McpAdapter`/`McpPerceiver` ditunda. |
| **Multi-peran / role-switching** | Hanya PA. (Tapi core TETAP bebas-peran — bedakan.) |
| **Otak remote untuk S1** | S1 = heuristik lokal. Hanya S2 yang remote. |
| **Async / konkurensi** | Loop sinkron. Async menunggu cadence menuntut. |
| **Skill di luar catatan + recall** | Tertipis. Tambah Skill = slice berikutnya. |
| **Pustaka konstitusi penuh** | Hanya batas keselamatan-kritis (tombol-mati, anti-fabrikasi, HITL, anti-penjilat). |
| **Spreading activation canggih** | Versi dasar cukup. |
| **GUI / web** | CLI saja. |
| **Persistensi working memory** | RAM transien. Hanya store yang persisten. |
| **Slice 2** | Sengaja **kosong** sampai slice 1 mengajari apa yang dibutuhkan. |

> **Aturan emas scope:** jika sebuah ide tak diperlukan agar *lingkaran menutup* atau *mirror test lulus*, ia OUT. Catat sebagai kandidat slice berikutnya, jangan bangun sekarang.

---

## Definisi "selesai"  `[TERKUNCI]`

Identik dengan `CLAUDE.md`:

1. **Lingkaran menutup** — `tick()` berputar kontinu.
2. **Mirror test lulus** — semua assert hijau (lapor-mutasi · `[ISI:]`-untuk-absen · Organ-C-menambat-pembohong · supremasi-tombol-mati).
3. **Core buta-platform** — tak ada `if role == "PA"` di `sadar/core/`.

---

## Pembeda dari VCBD (genre)

Blueprint ini **bukan** VCBD. VCBD = web-MVC (`entity→controller→view`, REST, skema relasional, UI, deploy/CI). SADAR = cognitive loop (`tick()` + organ, ports-and-adapters, Dosir in-memory + Markdown+vektor, CLI, mirror test). Tulang punggung berbeda, verifikasi berbeda. Jangan terapkan pola VCBD (controller, migrasi DB, endpoint) di sini.

---

## Grounding arsitektur

Konteks *mengapa* (the why) ada di paket **SADAR v0.4** (8 dokumen): `00` peta, `01` spine (Dosir, tick, organ A/B/C), `02–05` empat organ, `06` konstitusi & motivasi, `07` Peran & Skill. Blueprint ini tak menduplikasinya — ia merujuk. Jika ada keraguan desain konseptual, sumbernya di sana.
