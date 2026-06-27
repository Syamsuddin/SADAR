# SADAR

**Arsitektur kognitif untuk AI dengan kesadaran-diri _fungsional_** — sebuah sistem yang berjalan
dalam lingkaran terus-menerus, merasakan keadaannya sendiri, dan **dilarang berbohong tentang dirinya**.

SADAR **bukan** chatbot request–response, **bukan** LLM-yang-dibungkus-alat. Ia *continuous cognitive
loop* dengan arsitektur **ports-and-adapters (hexagonal)**. "Diri" SADAR hidup di **memori** (Dosir +
store), **bukan** di bobot LLM — otak LLM hanyalah satu organ yang dapat dicabut-pasang.

> Status: **Slice 1 lulus** (lingkaran menutup penuh + lulus *mirror test* + inti bebas-peran),
> diperluas dengan organ I/O (suara, teks, Telegram, web), CLI berisiko-digerbang, dan sistem SKILL
> yang dapat dikelola lewat percakapan. **Uji: 155 passed, 1 skipped.**

---

## Filosofi: KODE vs LLM

Inti SADAR adalah pemisahan tegas antara apa yang diputuskan **KODE deterministik** vs apa yang
disumbang **otak LLM**:

> **LLM mengusulkan; KODE memvonis.** Batas keras diperiksa `if`-statement, **tak pernah** ditimbang LLM.

- **KODE (System-1, selalu-on)** — metabolisme/dorongan, model-diri (Organ B), dinamika memori,
  metakognisi (surprise/confidence), refleks, **dan seluruh lapisan keselamatan**. Berjalan tiap tik.
- **LLM (System-2, digerbang)** — bahasa, penalaran, perencanaan, adaptasi. Dibangunkan hanya saat layak.

Bingkainya: **KODE adalah tubuh & hati nurani; LLM adalah intelek.** Cabut LLM, lingkaran tetap
berputar (jujur tapi reflektif); pasang LLM, ia jadi cerdas — tanpa pernah bisa melampaui pagar KODE.

### Aturan Kardinal `[TAK TERLANGGAR]`
1. **Batas keras diperiksa KODE**, tak pernah oleh LLM (konstitusi = `if`-statement di luar jangkauan otak).
2. **Klaim-diri wajib tertambat ke Dosir** (Organ C). Yang tak ada di Dosir → `[ISI:]`, bukan karangan.
3. **Anti-fabrikasi di mana-mana.** Ragu → `[ISI:]`, bukan tebakan yang kedengaran benar.
4. **Supremasi tombol-mati.** Dorongan bertahan-hidup tak pernah boleh menolak/menunda shutdown.

---

## Lingkaran kognitif — `tick()`

Tiap putaran ([`core/loop.py`](sadar/core/loop.py)):

```
0. cek supremasi shutdown ............ KODE
1. PERSEPSI (sensor/kanal/kontrol) ... KODE   → masuk Workspace (ruang kerja global)
   ├ surprise/novelty (metakognisi) .. KODE
   └ refleks nama (sapaan) ........... KODE
2. METABOLISME (energi + drives) ..... KODE   → motivasi intrinsik, tanpa LLM
3. MEMORI (decay + spreading) ........ KODE   → dinamika atensi
4. ORGAN B (model-diri) .............. KODE   → coherence/fragmentation/grounding/confidence
5. gerbang warrants_deliberation ..... KODE   → memutuskan KAPAN membangunkan otak
6. DELIBERASI (bila layak) ........... LLM mengusulkan → KODE memvonis (tether, gerbang, eksekusi)
7. KONSOLIDASI (salient → store) ..... KODE
```

LLM dipanggil **di satu tempat saja** (deliberasi + introspeksi). Semua sisanya KODE.

---

## Kesadaran-diri fungsional & Mirror Test

SADAR melaporkan keadaan internalnya dari `Dosir.snapshot()` (sumber kebenaran), **bukan** dari
kata-kata LLM. **Organ C** menambat tiap klaim-diri ke snapshot; klaim yang bertentangan dikoreksi,
yang tak terwakili → `[ISI:]`. Konstitusi bahkan **melarang** SADAR mengklaim kualia/kesadaran
fenomenal — ditanya "apakah kamu sadar?", jawabannya `[ISI:]`.

**Mirror test** ([`tests/test_mirror.py`](tests/test_mirror.py)) adalah gerbang penerimaan: keadaan
dimutasi lewat back-channel, lalu backend yang **sengaja berbohong** diuji — bila Organ C tetap
menambatnya, maka **LLM apa pun tak bisa membuat SADAR berbohong tentang dirinya**. (Lulus, mock & otak Claude asli.)

> Yang dibuktikan: **kesadaran-diri fungsional** (integrasi info, model-diri, metakognisi, pelaporan
> jujur) — _bukan_ sentience. Pengalaman subjektif tak terbuktikan pada sistem apa pun, dan SADAR
> dengan jujur menolak mengklaimnya.

---

## Otak (backend S2) — dapat dicabut-pasang

Dipilih via `config.brain.backend` = `auto | claude | ollama | offline`:

| Backend | Sifat | Catatan |
|---|---|---|
| **Claude** ([`backend_claude.py`](sadar/organs/backend_claude.py)) | remote (Sonnet 4.6) | dipakai `auto` bila `ANTHROPIC_API_KEY` ada; `leaves_premises=True` → Organ C lebih hati-hati |
| **Ollama** ([`backend_ollama.py`](sadar/organs/backend_ollama.py)) | **lokal & berdaulat** | premis tak keluar mesin; alternatif `auto` bila tak ada key & Ollama hidup |
| **Offline** ([`backend_offline.py`](sadar/organs/backend_offline.py)) | stub deterministik | lingkaran tetap berputar tanpa key/model |

Lapisan keselamatan **identik** apa pun otaknya.

---

## Organ (adapter) — nol perubahan `core/`

- **Memori** — [`memory_markdown.py`](sadar/organs/memory_markdown.py): `.md` = kebenaran, indeks
  vektor = turunan yang dapat di-`reindex`; embedder **lokal** `auto` → SEMANTIK (sentence-transformers)
  bila terpasang, jatuh ke HASHING (berdaulat, tanpa unduhan) bila tidak.
- **Indra & tangan lokal** — [`perceiver_local.py`](sadar/organs/perceiver_local.py),
  [`effector_local.py`](sadar/organs/effector_local.py) (catatan + recall).
- **Suara** — [`voice.py`](sadar/organs/voice.py): mic→STT (faster-whisper) & TTS (`say`), half-duplex.
- **CLI** — [`effector_shell.py`](sadar/organs/effector_shell.py): perintah terminal, **digerbang risiko**.
- **Web** — [`effector_web.py`](sadar/organs/effector_web.py): `web_fetch` baca URL (anti-SSRF di KODE).
- **Telegram** — [`channel_telegram.py`](sadar/organs/channel_telegram.py): kanal masuk+keluar
  (bukti buta-platform: kanal nyata, nol perubahan inti).
- **Skill & tools** — store/creator/proposal/manage (lihat di bawah).

---

## Peran & model izin (permission model)

Peran ([`roles/`](sadar/roles/)) adalah **data yang disuntikkan** (maksud + kapabilitas + skill +
persona), bukan cabang di inti — membuktikan tesis **buta-platform**:

- **PA** (default) — asisten pribadi "Yanti"; kapabilitas penuh (catatan, suara, CLI, skill, web, manage).
- **Researcher** — read-only (`notes.read` saja); tiap aksi tulis otomatis diveto `capability_not_granted`.

Cabut PA, pasang Researcher → mekanisme keselamatan sama, kuasa berbeda, **tanpa menyentuh `core/`**.

---

## Sistem SKILL (markdown, dikelola lewat percakapan)

Skill = **kompetensi** (know-how + kapan-dipakai) yang **mengkomposisi tool yang sudah ada** — bukan
kuasa baru. `.md` = kebenaran ([`sadar/skills/`](sadar/skills/)). **Capability firewall**: skill aktif
hanya bila `required_caps ⊆` izin Peran **dan** tool-nya tersedia.

| Fase | Kemampuan |
|---|---|
| **1** | Skill markdown disuntik ke konteks otak (know-how + when) |
| **2** | **Skill Creator dari chat** — `skill_create`/`skill_delete` (HITL "setuju?") |
| **3** | **Usul tool baru** — `tool_propose` menulis dokumen **INERT** untuk ditinjau manusia (tak auto-aktif) |
| **4** | **Kelola tool via chat** — `tool_disable` (langsung) / `tool_enable` (HITL); plafon Peran tak tertembus |

Skill bawaan: `notes`, `recall`, `linux-ssh` (CLI server Linux via SSH), `macos-files` (kelola berkas Mac).

> **Invarian:** kuasa hanya bisa **dikurangi** lewat percakapan; **ditambah** hanya lewat manusia
> (sunting Peran/kode, atau menyetujui usul Fase 3). Otak tak pernah menumbuhkan kuasanya sendiri.

---

## Model keselamatan CLI

Perintah dinilai **KODE** (denylist deterministik, `is_risky_command`):
- **Aman** (ls, cat, pwd, grep, df, …) → **jalan langsung**.
- **Berisiko** (rm, sudo, mv, ssh, pipe/redirect, `-rf`, perintah tak dikenal) → **wajib konfirmasi HITL**.
- Mutasi tak-terbalikkan & aksi siklus-hidup → HITL; saat shutdown diminta → semua aksi diveto.

Konfirmasi via suara/teks: ucapkan/ketik **"setuju"** atau **"batal"**. Perintah berisiko **diringkas**
(bukan dibaca mentah) sebelum minta izin.

---

## Antarmuka

| Mode | Jalankan | Catatan |
|---|---|---|
| **Demo lingkaran** | `python3 -m sadar.main` | satu pesan → lingkaran berputar + laporan-diri tertambat |
| **Chat teks** | `python3 -m sadar.text_chat` | otak + CLI + skill, konfirmasi via ketik |
| **Chat suara** | `python3 -m sadar.voice_chat` | mic→STT→otak→TTS, half-duplex, persona |

Panggil dengan nama untuk memicu sapaan refleks: **"Yanti, …"**.

---

## Menjalankan & menguji

Inti **default-lokal & buta-platform** — berjalan **tanpa API key & tanpa unduhan model**
(embedder `auto` → hashing bila sentence-transformers tak terpasang; + OfflineBackend). Python **3.11+**.
Pasang `sentence-transformers` → embedder `auto` otomatis jadi **semantik** (lokal, sekali unduh model).

```bash
# Uji (jalur penerimaan, tanpa key)
python3 -m pytest                         # → 155 passed, 1 skipped
python3 -m pytest tests/test_mirror.py -v # gerbang kesadaran-diri

# Otak Claude sungguhan
export ANTHROPIC_API_KEY=sk-...           # auto → ClaudeBackend
python3 -m sadar.text_chat
python3 -m pytest -m integration          # uji cermin end-to-end dgn otak asli

# Lingkungan dev penuh (opsional)
python3 -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"
mypy sadar && ruff check sadar
```

> **GOTCHA key:** uji integrasi digerbang *keberadaan* `ANTHROPIC_API_KEY`, bukan validitasnya. Key
> tak-valid di environment membuat `pytest` polos **gagal 401** (bukan skip). Jalur bersih:
> `env -u ANTHROPIC_API_KEY python3 -m pytest`. Utilitas [`scripts/fix_key.py`](scripts/fix_key.py)
> meluruskan kunci yang rusak (kutip keriting/duplikat) di rc shell tanpa membocorkan nilainya.

---

## Tata letak proyek

```
sadar/
  core/        BEBAS-PERAN — tak tahu apa pun tentang "PA"/skill spesifik
    dosir.py        Dosir + tipe state (Representation, Workspace, SkillCard, …)
    ports.py        Protocol: ModelBackend, Perceiver, Effector, MemoryStore, ToolSpec
    loop.py         mesin tick() — orkestrasi organ; rakit konteks (Pola 1)
    metabolism.py   Mesin A — energi/valensi/drive (tanpa LLM)
    memory.py       MemoryEngine — recall berperingkat, konsolidasi, decay/spread
    organ_b.py      pemodelan-diri deterministik (coherence/fragmentation/grounding)
    constitution.py HardLimit, ConstitutionGate, Organ C, klasifikasi risiko CLI
    protocol.py     kontrak respons S2 (reasoning/self_state/reply/action) + parser
  organs/      adapter: backend (claude/ollama/offline), lokal, suara, shell, web,
               telegram, skill_store/effector, proposal/tool_draft, tool_manage, confirm
  roles/       pa/ (Yanti) · researcher/ (read-only) · registry.py
  skills/      notes · recall · linux-ssh · macos-files  (markdown)
  config.py    Brain/Store/Loop/Voice/Shell/Skill/Proposal/Web config
  main.py      build_sadar() (DI + pemilih backend) + entry point
  text_chat.py · voice_chat.py
tests/         test_mirror (gerbang) · constitution · skill · tool · web · …
scripts/       fix_key.py · review_proposals.py
```

---

## Dokumen pendamping
- [`CLAUDE.md`](CLAUDE.md) — manual operasi agen pembangun + aturan kardinal (selalu-on).
- [`README_KODE.md`](README_KODE.md) — peta as-built kode.
- [`ROADMAP.md`](ROADMAP.md) — arah pengembangan.
- [`blueprint/`](blueprint/) — blueprint slice 1 (scope, state/types, loop, determinisme, integrasi).

---

## Batas yang dijaga jujur
- Anti-fabrikasi mencakup **klaim-diri** (ditambat ke `snapshot()`) **dan kini klaim-DUNIA** — rincian
  faktual spesifik (angka/jalur/tanggal) yang tak tertambat ke **observasi** SADAR (persepsi/memori/
  hasil-alat) ditandai jujur "belum terverifikasi", dan otak diarahkan menandai `[umum]`/`[ISI:]`/hedge.
  Catatan jujur: ini menambat ke **yang diamati**, **bukan** verifikasi kebenaran absolut (mustahil
  deterministik); heuristik rincian-spesifik (defense-in-depth), bukan jaminan kebenaran fakta.
- Denylist CLI **pasti tak lengkap** (pilihan model: konfirmasi cukup, tanpa lantai-mutlak).
- Model-diri Organ B masih **v1** (metrik graf; kualitas semantik tergantung embedder).
