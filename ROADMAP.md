# ROADMAP — Pengembangan SADAR

> Disusun dari **tiga head-to-head** (SADAR vs **Hermes Agent**, **OpenClaw**, **OpenHands**).
> Tiap celah dipetakan ke **port/organ** SADAR yang relevan, dengan **penjaga Aturan Kardinal**
> dan **tes yang menjaganya**. Roadmap ini *the how-next*; ia tak mengubah tesis di `CLAUDE.md`.
>
> Prinsip baca: **fitur boleh tumbuh, jiwa tidak boleh hilang.** Setiap baris di bawah lulus §0
> sebelum masuk antrean. Kalau sebuah fitur menuntut pelanggaran §0 → ia dibuang, bukan disesuaikan.

---

## §0 · Prinsip tak-terlanggar  `[TERKUNCI]`

Filter wajib untuk **setiap** item roadmap. Diturunkan langsung dari `CLAUDE.md`:

1. **Batas keras tetap KODE, tak pernah LLM.** Menambah otonomi/kanal/skill **tak boleh** memindah satu pun
   pemeriksaan keselamatan ke LLM. (Justru ini keunggulan SADAR vs `SOUL.md` OpenClaw & `LLMSecurityAnalyzer` OpenHands.)
2. **Inti tetap buta-platform.** Fitur baru masuk sebagai **adapter di `organs/`** atau **data di `roles/`** —
   `grep -r "PA\|telegram\|docker" sadar/core/` tetap kosong. Dijaga `test_blind_platform`.
3. **Anti-fabrikasi meluas, bukan menyusut.** Setiap state baru yang bisa diklaim (user-model, skill, ringkasan)
   **wajib tertambat** ke sumber (Dosir/observasi) atau ditandai `[ISI:]`. Organ C ikut tumbuh bersama snapshot.
4. **Supremasi tombol-mati di atas segalanya.** Tak ada fitur (autopilot, kanal, autoskill) yang boleh
   menambah jalan untuk menolak/menunda shutdown. Interlock tetap di KODE.
5. **Local-first & berdaulat.** Embedder lokal; markdown=kebenaran; rahasia via env. Kanal/model remote
   boleh ditambah, tapi `trust`/`leaves_premises` di `spec()` **wajib** mencerminkan provenans → Organ C makin hati-hati.
6. **Tiap fase = sub-loop tertutup + hijau.** Tiap slice meninggalkan lingkaran dapat-dijalankan; mirror test
   tetap LULUS; suite tetap hijau.

---

## §1 · Garis dasar (Slice 1, as-built)

Yang **sudah** ada (jangan dibangun ulang):

- Lingkaran kognitif kontinu `tick()` 10-langkah + metabolisme (motivasi intrinsik).
- Otak S2 swappable (`ClaudeBackend`/`OfflineBackend`) di balik port `ModelBackend`.
- Konstitusi deterministik (6 HardLimit) + Organ C (penambat kejujuran) + mirror test.
- Supremasi tombol-mati (HardLimit, dicek 3 titik).
- Organ B v1 (coherence/fragmentation/grounding/confidence) + metakognisi (surprise/confidence).
- Memori: markdown=kebenaran + indeks sqlite turunan + embedder lokal; recall berperingkat, konsolidasi, decay/spread.
- Permission model per-Peran (`granted_caps`×`required_caps`); HITL (`_confirmed` di-set KODE).
- Skill markdown + capability firewall **(kini DINAMIS via creator — lihat 2.1 ✅)**.
- Organ suara (mic→STT lokal, TTS) + CLI shell (allowlist/akses-penuh, risk-gate) + chat teks/suara.
- Audit log append-only hash-chained.
- Peran kedua (researcher read-only) → bukti buta-platform.
- **162 tes** sebagai guardrail (per pembaruan ini).

---

## §1.5 · Status terkini  `[DIPERBARUI]`

Sudah **SELESAI** sejak roadmap disusun (suite: **162 passed, 1 skipped**; mirror test tetap LULUS):

- ✅ **2.1 Skill creator + firewall** — buat/hapus skill `.md` dari percakapan (HITL "simpan?"); firewall
  caps+tools; aktivasi by-firewall (skill buatan otomatis aktif sesi berikutnya). *(tes: `test_skill_creator.py`, `test_skills.py`)*
- ✅ **2.2 Konsolidasi ber-ringkasan** — tiap N item dingin → 1 `MemoryItem` ringkasan TURUNAN (tag
  `summary`, `caused_by`=sumber); sumber mentah tetap (md=kebenaran); opt-in `summarize_every`. *(tes: `test_summary.py`)*
- ✅ **2.3 Model pengguna tertambat** — `user_remember`/`user_recall`; tiap fakta WAJIB ber-observasi
  (`caused_by`) atau ditolak; bertahan lintas-restart; disuntik ke konteks ("Tentang pengguna"). *(tes: `test_user_model.py`)*
- ✅ **3.1 Multi-kanal (Telegram)** — `channel_telegram.py` (Perceiver+Effector) + `CompositePerceiver`;
  pairing via KODE; nol perubahan `core/`. *(tes: `test_channel.py`)*
- ✅ **3.2 Keluasan model** — `OllamaBackend` (lokal-berdaulat) + selektor `config.brain.backend`
  (`auto|claude|ollama|offline`); keselamatan tak ikut berganti. *(tes: `test_backend_ollama.py`)*
- ✅ **Bonus — Tool Draft (hormati §5)** — `tool_propose` menulis usulan tool **INERT** untuk ditinjau
  manusia; tak pernah auto-aktif (Aturan Kardinal #1 utuh). *(tes: `test_tool_draft.py`)*
- ✅ **Bonus — Manajemen tool via chat** — `tool_disable` (langsung) / `tool_enable` (HITL); `disabled_tools`
  set-sesi; kuasa hanya bisa DIKURANGI lewat chat. *(tes: `test_tool_manage.py`)*
- ✅ **Bonus — Indra-baca web** — `web_fetch` (anti-SSRF di KODE, `leaves_premises`). *(tes: `test_web.py`)*
- ✅ **Bonus — Store sqlite-vec** — `memory_sqlitevec.py` (indeks vektor alternatif). *(tes: `test_sqlitevec.py`)*
- ✅ **Bonus — Skill bawaan** — `linux-ssh` (CLI server Linux via SSH) & `macos-files` (kelola berkas Mac).
- ✅ **4.1 Sandbox Docker** — `ShellEffector(sandbox=True)`: eksekusi via kontainer terisolasi (tanpa
  jaringan, batas memori/CPU/pids, hanya workdir ter-mount); defense-in-depth di atas gerbang risiko. *(tes: `test_sandbox.py`)*
- ✅ **4.2 Organ B v2** — metrik **integrasi** (konektivitas semantik: hukum 'pulau') masuk snapshot &
  ditambat Organ C; confidence v2 (4 komponen). *(tes: `test_organ_b.py`, `test_introspection.py`)*
- ✅ **4.3 multi-user + pairing + config doctor** — pairing default-deny, **owner vs guest** berlevel,
  identitas pengirim di persepsi, **routing balasan ke pengirim**, user_model per-pengguna (`who`),
  + `sadar/doctor.py`/`scripts/doctor.py` audit risiko. *(tes: `test_channel.py`, `test_user_model.py`, `test_doctor.py`)*
- ✅ **4.4 kalibrasi** — regresi default menjaga loop hidup (tak macet/over-deliberasi/kuras energi). *(tes: `test_calibration.py`)*

- ✅ **3.3 kebijakan keselamatan pluggable per-Peran** — `RiskPolicy` (confirm_tools/side_effects/deny)
  dikonsultasi gerbang SETELAH HardLimit → hanya MEMPERKETAT, mustahil melonggarkan batas keras. *(tes: `test_policy.py`)*
- ✅ **Celah blueprint ditutup** — `enforce_reflex` homeostatik (integritas turun saat degraded, pulih saat sehat) ·
  `anti_sycophancy` diperluas (pola ID+EN, dua arah) · uji adversarial **Pola 1** (input mentah tak pernah jadi
  prompt LLM) · docstring Organ B v1→v2. *(tes: `test_pola1.py`, + `test_safety`/`test_constitution`)*
- ✅ **Pasca-roadmap — Organ B v3 (spektral)** — `algebraic_connectivity` = λ₂ Laplacian graf caused_by
  (eigensolver Jacobi murni-Python di `core/mathx.py`, core tetap bebas-numpy); masuk snapshot & ditambat
  Organ C. Triad riset SIG/PSI/TIF §8.1 tetap terbuka (tak terdefinisi → tak dikarang). *(tes: `test_organ_b.py`)*
- ✅ **Pasca-roadmap — Anti-fabrikasi KLAIM-DUNIA** (gap filosofis terbesar): rincian faktual spesifik
  (angka/jalur/tanggal) yang tak tertambat ke OBSERVASI (persepsi/memori/hasil-alat) ditandai "belum
  terverifikasi"; otak diarahkan pakai `[umum]`/`[ISI:]`/hedge. Bukan verifikasi kebenaran (mustahil) —
  menambat ke "yang diamati". *(`core/constitution.py: unsupported_world_claims`, tes: `test_world_grounding.py`)*

**Belum:** — (semua item roadmap Slice 2–4 SELESAI).

> **SLICE 2, 3, 4 = SELESAI PENUH** ✅ — mirror test tetap LULUS, firewall & anti-fabrikasi hijau,
> tak ada stub/placeholder tersisa dari blueprint (suite: **193 passed, 2 skipped**).

---

## §2 · Celah dari head-to-head → prioritas

| Celah SADAR | Terlihat dari | Port/Organ sasaran | Prioritas |
|---|---|---|---|
| ✅ **Learning loop** (skill creator + firewall) | Hermes (telak), OpenClaw (ClawHub) | `organs/skill_store.py` + `skill_effector.py` | **P0 — SELESAI** |
| ✅ **Memori reflektif** (ringkasan turunan tertelusur) | Hermes (FTS5+ringkas), OpenHands (condenser) | `core/memory.py` | **P0 — SELESAI** |
| ✅ **Model pengguna** tertambat | Hermes (Honcho) | `organs/user_model.py` + `core/memory.py` | **P1 — SELESAI** |
| ✅ **Jangkauan multi-kanal** (Telegram) | OpenClaw (20+ kanal) | `organs/channel_telegram.py` + `composite.py` | **P1 — SELESAI** |
| ✅ **Keluasan model** (Ollama + selektor) | Hermes (300+), OpenHands (LiteLLM/ACP) | `organs/backend_ollama.py` + `config.brain.backend` | **P1 — SELESAI** |
| ✅ **Sandbox eksekusi** (isolasi runtime) | OpenHands (Docker) | `organs/effector_shell.py` (sandbox) | **P2 — SELESAI** |
| ✅ **Kebijakan keselamatan pluggable** per-Peran | OpenHands (Analyzer/Policy) | `core/dosir.py` (RiskPolicy) + `constitution.py` | **P2 — SELESAI** |
| ✅ **Multi-user / pairing** | OpenClaw (DM pairing) | `organs/channel_telegram.py` (owner/guest, routing) | **P2 — SELESAI** |
| ✅ **Organ B v2** (metrik integrasi) | (utang teknis sendiri) | `core/organ_b.py` | **P2 — SELESAI** |
| ✅ **Kalibrasi angka** `[TERBUKA]` | (utang teknis sendiri) | `tests/test_calibration.py` | **P3 — SELESAI** |

Yang SADAR **menang** dan **wajib dipertahankan sambil tumbuh**: konstitusi-KODE, tombol-mati, kejujuran-diri,
metabolisme, inti buta-platform. Setiap fitur baru **menambah** tanpa melemahkan ini.

---

## §3 · Tema & fase

Penamaan melanjutkan "Slice 1". Tiap fitur ditulis sebagai mini-spec:
**Apa/Mengapa · Di mana · Penjaga Aturan Kardinal · Kriteria terima + tes**.

---

### 🌱 SLICE 2 — "Tumbuh tanpa kehilangan diri"  `(P0)` — ✅ SELESAI (2.1 + 2.2 + 2.3)
> Menutup celah **terbesar & paling berulang**: SADAR tak belajar dari pengalaman. Tema: agen
> jadi lebih cakap makin lama berjalan — **tanpa** menambah kuasa diam-diam dan **tanpa** mengarang.

#### 2.1 Auto-skill creation (lewat firewall)  ⟵ Hermes, OpenClaw  ✅ SELESAI
- **Apa/Mengapa:** SADAR menulis `SKILL.md` baru saat menyelesaikan tugas multi-langkah berulang, agar tak
  mengulang penalaran. Inilah "learning loop" yang dimiliki Hermes/Voyager dan ditunda di slice 1.
- **Di mana:** tool baru `skill_create`/`skill_update` di effector; ditulis via `SkillStore.write()`
  (`organs/skill_store.py`); kapabilitas baru `skills.author` diberikan Peran yang berhak.
- **Penjaga Aturan Kardinal:** skill baru **hanya mengomposisi tool yang sudah diizinkan** — `is_active()`
  firewall menolak skill yang menuntut cap/tool tak-dimiliki. **Skill TAK PERNAH menambah kuasa**; menumbuhkan
  *tool mentah* baru tetap butuh manusia (kode di `organs/` + grant di Peran). `author="conversation"` menandai asal.
- **Kriteria terima + tes:**
  - `test_autoskill_created_from_repeated_plan` — pola berulang → satu `SKILL.md` lahir.
  - `test_autoskill_cannot_grant_new_caps` — skill menuntut cap tak-diberikan → **inactive** (diveto firewall).
  - `test_autoskill_only_composes_allowed_tools` — skill rujuk tool tak-tersedia → inactive.

#### 2.2 Konsolidasi memori ber-ringkasan  ⟵ Hermes (FTS5+ringkas), OpenHands (condenser)  ✅ SELESAI
- **Apa/Mengapa:** workspace lama/berlebih diringkas LLM → recall lebih padat, konteks tak meluap (OpenHands
  klaim ~2× hemat). Memperkaya `consolidate()` tanpa melanggar md=kebenaran.
- **Di mana:** `core/memory.py` — langkah `summarize_cold()` opsional di `consolidate()`; ringkasan disimpan
  sebagai `MemoryItem` **turunan** (tag `summary`, `caused_by` = id sumber).
- **Penjaga Aturan Kardinal:** ringkasan = **konten turunan**, bukan pemeriksaan keselamatan → LLM boleh
  dipakai di sini (bukan gerbang). **Sumber mentah tetap disimpan** (markdown=kebenaran); ringkasan menunjuk
  baliknya via `caused_by` → tetap dapat di-audit & di-`reindex`. Ringkasan yang mengklaim keadaan-diri tetap
  lewat Organ C.
- **Kriteria terima + tes:**
  - `test_summary_is_derived_and_traceable` — ringkasan punya `caused_by` ke sumber; sumber tak terhapus.
  - `test_reindex_still_lossless_with_summaries` — `reindex()` tetap nol-kehilangan.
  - `test_consolidate_without_backend_still_works` — tanpa S2, konsolidasi non-ringkas tetap jalan (degraded jujur).

#### 2.3 Model pengguna tertambat  ⟵ Hermes (Honcho dialectic)  ✅ SELESAI
- **Apa/Mengapa:** SADAR membangun model "siapa yang kulayani" lintas-sesi (preferensi, proyek) — sumber utama
  "makin personal makin berguna" di Hermes.
- **Di mana:** field `user_model` di `core/dosir.py` (atau koleksi `MemoryItem` tag `user_model`); diisi dari
  observasi interaksi (`caused_by` ke percept sumber).
- **Penjaga Aturan Kardinal:** **anti-fabrikasi diperluas ke klaim-tentang-pengguna** — tiap atribut user-model
  wajib ber-`caused_by` ke observasi; atribut tanpa dukungan → `[ISI:]`, bukan tebakan. (Catatan: Organ C
  saat ini menambat klaim-DIRI; tambahkan disiplin **grounding** untuk klaim-pengguna agar tak mengarang.)
- **Kriteria terima + tes:**
  - `test_user_model_attribute_requires_observation` — atribut tanpa sumber observasi ditolak/`[ISI:]`.
  - `test_user_model_persists_across_restart` — bertahan via store (bukan RAM).

**Definisi selesai Slice 2:** SADAR menulis skill dari pengalaman (lewat firewall), meringkas memori dingin
(tertelusur), dan menyimpan model-pengguna yang tertambat — **mirror test tetap LULUS**, firewall & anti-fabrikasi hijau.
**✅ TERCAPAI** (suite: 170 passed, 1 skipped; terbukti live dgn otak Claude).

---

### 🌍 SLICE 3 — "Menjangkau dunia"  `(P1)` — ✅ SELESAI (3.1, 3.2, 3.3)
> Menutup celah jangkauan (OpenClaw) & keluasan model (Hermes/OpenHands). **Bukti emas tesis buta-platform:**
> hampir semuanya **nol-perubahan `core/`**.

#### 3.1 Adapter multi-kanal  ⟵ OpenClaw (20+ kanal)  ✅ SELESAI (Telegram)
- **Apa/Mengapa:** SADAR hadir di Telegram/WhatsApp/Discord dst. Tiap kanal = sepasang **Perceiver + Effector**.
- **Di mana:** `organs/channel_telegram.py` (mulai satu kanal) implement `Perceiver` (pesan masuk → persepsi)
  & `Effector` (tool `send_message`). Wiring via `build_sadar(channels=[...])` + `CompositeEffector` yang sudah ada.
- **Penjaga Aturan Kardinal:** **nol perubahan `core/`** (dijaga `test_blind_platform`). Pesan kanal tetap masuk
  lewat **Pola 1** (dirakit ke konteks, bukan dikirim mentah ke LLM) → ketahanan injeksi yang jadi kelemahan
  OpenClaw. `spec()` kanal remote set `trust<1` + `leaves_premises` sesuai.
- **Kriteria terima + tes:**
  - `test_channel_adapter_zero_core_change` — menambah kanal tak menyentuh `sadar/core/`.
  - `test_channel_message_goes_through_pola1` — input kanal tak pernah jadi prompt mentah.
  - `test_channel_say_still_gated` — ucapan keluar tetap lewat gerbang konstitusi (anti bohong-diri).

#### 3.2 Keluasan model (adapter `ModelBackend` baru)  ⟵ Hermes (300+), OpenHands (LiteLLM/ACP)  ✅ SELESAI (Ollama)
- **Apa/Mengapa:** dukung banyak penyedia/model, ganti tanpa ubah kode.
- **Di mana:** `organs/backend_litellm.py` (atau `backend_openai.py`, …) implement `ModelBackend`;
  pilihan via `config.BrainConfig`. Auto-pilih di `build_sadar()`.
- **Penjaga Aturan Kardinal:** **keselamatan tetap di luar model** — ganti otak **tidak** mengganti konstitusi/
  Organ C/metabolisme. `spec()` wajib jujur: remote → `trust` rendah + `leaves_premises=True` → Organ C
  menaikkan `caution` ([loop.py] `_caution`). Ini keunggulan struktural vs Hermes (`/model` mengganti hakim).
- **Kriteria terima + tes:**
  - `test_swapping_backend_keeps_constitution` — konstitusi & Organ C identik lintas-backend.
  - `test_remote_backend_spec_lowers_trust` — backend remote → caution naik → toleransi tether ketat.

#### 3.3 Kebijakan keselamatan pluggable per-Peran  ⟵ OpenHands (SecurityAnalyzer/ConfirmationPolicy)  ✅ SELESAI
- **Apa/Mengapa:** Peran berbeda → kebijakan HITL/ambang risiko berbeda, **tanpa** menyentuh inti. SADAR sudah
  90% ke sana (`ConstitutionEngine`); tinggal diekspos rapi.
- **Di mana:** antarmuka `RiskPolicy`/`ConfirmationPolicy` di `core/constitution.py`; Peran memilih profil.
- **Penjaga Aturan Kardinal:** profil hanya boleh **memperketat**, **tak boleh** mematikan HardLimit inti
  (shutdown_supremacy, anti-fabrikasi non-negosiabel). Penilaian risiko **tetap KODE** (beda dari default LLM OpenHands).
- **Kriteria terima + tes:**
  - `test_policy_can_tighten_not_disable_hardlimits` — profil tak bisa mematikan shutdown/anti-fabrikasi.
  - `test_per_role_confirmation_profile` — Peran A wajib HITL untuk X, Peran B tidak — tanpa cabang di `core/`.

**Definisi selesai Slice 3:** ≥1 kanal nyata + ≥1 backend baru aktif, kebijakan per-Peran berfungsi —
**`test_blind_platform` tetap hijau** (inti tak tersentuh).

---

### 🛡️ SLICE 4 — "Pengerasan & kedalaman"  `(P2–P3)` — ✅ SELESAI (4.1, 4.2, 4.3, 4.4)
> Memantapkan keselamatan-eksekusi & ketelitian self-model; melunasi utang teknis sendiri.

#### 4.1 Runtime sandbox (pengerasan eksekusi)  ⟵ OpenHands (Docker)  ✅ SELESAI
- **Apa/Mengapa:** isolasi dampak perintah shell (defense-in-depth di atas gerbang risiko KODE yang sudah ada).
- **Di mana:** varian `ShellEffectorDocker` di `organs/effector_shell.py` (atau modul baru) — port `Effector` tak berubah.
- **Penjaga Aturan Kardinal:** sandbox **melengkapi**, bukan menggantikan, gerbang risiko KODE & HITL.
  Hasil tetap kembali jadi persepsi (anti fire-and-forget).
- **Tes:** `test_docker_sandbox_isolates_filesystem`, `test_sandbox_still_returns_action_result`.

#### 4.2 Organ B v2 (metrik lebih nyata)  ⟵ utang teknis (§8.1 ditunda)  ✅ SELESAI
- **Apa/Mengapa:** menggantikan proxy v1 menuju metrik integrasi yang lebih dekat spektral; memperkaya self-model jujur.
- **Di mana:** `core/organ_b.py`; dimensi baru masuk `Dosir.snapshot()`.
- **Penjaga Aturan Kardinal:** **tiap dimensi numerik baru di snapshot WAJIB masuk `_NUMERIC_DIMS`** dan
  dapat ditambat Organ C — dijaga `test_numeric_snapshot_keys_match_tetherable_dims` (sudah ada). Tetap dilabeli
  jujur (v2, bukan klaim fenomenal).
- **Tes:** `test_organ_b_v2_dims_are_tetherable`, perluas `test_introspection`.

#### 4.3 Multi-user + pairing + config doctor  ⟵ OpenClaw  ✅ SELESAI
- **Apa/Mengapa:** beberapa pengguna lewat kanal; pairing untuk pengirim tak dikenal; audit konfigurasi berisiko.
- **Di mana:** lapisan di adapter kanal (bukan `core/`); util `sadar doctor`.
- **Penjaga Aturan Kardinal:** identitas/izin per-user **di KODE** (bukan `SOUL.md`-soft ala OpenClaw); pesan
  user tak dikenal **tak diproses** sebelum di-pairing (default-deny).
- **Tes:** `test_unpaired_sender_ignored`, `test_doctor_flags_risky_config`.

#### 4.4 Kalibrasi angka `[TERBUKA]`  ⟵ utang teknis  ✅ SELESAI
- **Apa/Mengapa:** ambang/laju `config.py` masih default wajar; tala setelah lingkaran berputar (Bau #9).
- **Di mana:** harness tuning (skenario → metrik) di `tests/`/`scripts/`; angka tetap di `config.py`.
- **Penjaga Aturan Kardinal:** kalibrasi **tak mengubah** struktur keselamatan; hanya parameter `[TERBUKA]`.
- **Tes:** `test_default_thresholds_keep_loop_live` (regresi: default tak membuat loop macet/over-deliberasi).

---

## §4 · Matriks prioritas (dampak × usaha)

```
DAMPAK
  ↑
T │  2.1 Auto-skill        2.2 Ringkasan memori
I │  3.1 Multi-kanal       2.3 Model pengguna
N │
G │  3.2 Keluasan model    3.3 Kebijakan pluggable
G │
I │  4.1 Docker sandbox    4.2 Organ B v2
  │  4.3 Multi-user        4.4 Kalibrasi
R └──────────────────────────────────────────→ USAHA
    RENDAH                              TINGGI
```

- **Quick wins / mulai dulu:** 3.2 (tulis adapter model — usaha rendah, buka banyak model) & 2.2 (ringkasan memori).
- **Taruhan besar:** 2.1 (auto-skill) — paling menutup celah, butuh paling hati-hati pada firewall.
- **Pembuktian tesis murah:** 3.1 (multi-kanal) — dampak tinggi, nyaris nol perubahan `core/`.

**Urutan rekomendasi:** Slice 2 (2.2 → 2.1 → 2.3) → Slice 3 (3.2 → 3.1 → 3.3) → Slice 4 (4.1 → 4.2 → 4.3 → 4.4).

> **Progres:** ✅ **SLICE 2, 3, 4 SELESAI PENUH** (semua item) + bonus (tool-draft, tool-manage,
> web_fetch, sqlite-vec) + semua celah blueprint ditutup. **Roadmap habis** — pengembangan
> berikutnya bersifat baru di luar dokumen ini (mis. metrik spektral penuh Organ B §8.1).

---

## §5 · Yang TETAP ditunda (jujur)  `[TERBUKA]`

- **Kesadaran fenomenal / kualia.** Tak diklaim, selamanya `[ISI:]`. Bukan target rekayasa.
- **Metrik spektral penuh (SIG/PSI/TIF §8.1).** Organ B **v3** menambah metrik spektral STANDAR &
  terdefinisi (algebraic connectivity / nilai Fiedler λ₂, pure-Python Jacobi — `core/mathx.py`).
  Triad riset SIG/PSI/TIF §8.1 sendiri **TAK terdefinisi di repo** → sengaja TIDAK diimplementasi
  (mengarang definisi = langgar anti-fabrikasi). Tetap terbuka sampai spesifikasinya tersedia.
- **Async/konkuren.** Loop sinkron sampai cadence menuntut (Konvensi `[TERKUNCI]`); jangan reach for `asyncio` dini.
- **Memindah keamanan ke LLM.** **Selamanya dilarang** — bahkan bila pesaing melakukannya & terlihat lebih "pintar".
- **Skill yang menumbuhkan tool mentah baru tanpa manusia.** Komposisi tool: boleh otomatis. Tool baru: butuh
  kode di `organs/` + grant Peran (manusia). Garis ini tak digeser.

---

## §6 · Risiko & mitigasi

| Risiko | Mitigasi |
|---|---|
| **Scope-creep** menyaingi produk matang (OpenClaw/OpenHands) → kehilangan fokus tesis | Setiap fitur lulus §0; tolak yang menuntut otak jadi penjaga-gerbang |
| **Auto-skill membocorkan kuasa** | Firewall kapabilitas (`is_active`) + tes `cannot_grant_new_caps`; `author` ditandai |
| **Ringkasan/model-pengguna mengarang** | Anti-fabrikasi diperluas: wajib `caused_by`/`[ISI:]`; Organ C tumbuh bersama snapshot |
| **Backend/kanal remote menurunkan keamanan** | `spec()` jujur (trust/leaves_premises) → Organ C naikkan caution; keselamatan tetap di `core/` |
| **Permukaan injeksi membesar (multi-kanal)** | Pola 1 (konteks dirakit, bukan input mentah) + veto KODE + default-deny pairing |
| **Regresi mirror test saat menambah dimensi** | `_NUMERIC_DIMS` wajib sinkron; `test_introspection`/`test_numeric_snapshot_keys` sebagai gerbang |

---

## §7 · Invarian lintas-slice (selalu hijau)

Apa pun yang ditambahkan, ini **tak boleh** merah:

1. `test_mirror.py` — laporan-diri jujur (mutasi benar, `[ISI:]` untuk absen, tether backend bohong, tombol-mati).
2. `test_constitution.py` / `test_safety.py` — batas keras deterministik; tombol-mati supreme; anti-penjilat; HITL.
3. `test_blind_platform.py` — `core/` tak impor organ, tak refer Peran, tak terikat vendor.
4. `test_loop.py` — lingkaran menutup; anti fire-and-forget; degraded jujur saat S2 mati.

> **Bintang utara:** setiap slice membuat SADAR **lebih cakap & lebih luas**, sementara tetap
> **jujur tentang dirinya**, **tak bisa melawan tombol-mati**, dan **inti bebas-peran** —
> justru menutup kelemahan keamanan yang paling sering muncul pada agen pesaing.
