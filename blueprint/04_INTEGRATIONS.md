# 04 · INTEGRATIONS — Adapter Konkret SADAR Slice 1

> Di VCBD ini "kontrak REST + skema DB". Di SADAR ini **adapter yang mengimplementasikan 4 port** (`01`). Semua di `sadar/organs/` + Peran di `sadar/roles/pa/`. Core tak pernah mengimpor file-file ini langsung — hanya lewat Protocol.

---

## 1. `ClaudeBackend` → `ModelBackend` (otak S2)  `[TERKUNCI]`

File: `sadar/organs/backend_claude.py`. Model: **`claude-sonnet-4-6`** (Haiku `claude-haiku-4-5-20251001` untuk proto murah). **S2 only.**

```python
import os
from anthropic import Anthropic
from sadar.core.ports import ModelBackend, BackendSpec

class ClaudeBackend:                       # implements ModelBackend
    def __init__(self, model: str = "claude-sonnet-4-6", max_tokens: int = 1024):
        self.client = Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])  # JANGAN hardcode
        self.model = model
        self.max_tokens = max_tokens

    def complete(self, system: str, prompt: str, *, tier="sys2") -> str:
        assert tier == "sys2", "ClaudeBackend hanya melayani S2 (slice 1)"
        msg = self.client.messages.create(
            model=self.model, max_tokens=self.max_tokens,
            system=system,                       # identitas+konstitusi+maksud (dirakit SADAR)
            messages=[{"role": "user", "content": prompt}],  # KONTEKS RAKITAN, bukan input mentah
        )
        return "".join(b.text for b in msg.content if b.type == "text")

    def spec(self) -> BackendSpec:
        return BackendSpec(name="claude-sonnet-4.6", provenance="remote",
                           trust=0.5, tiers=["sys2"], leaves_premises=True)

    def available(self) -> bool:
        # cek ringan untuk degraded mode: env ada + (opsional) ping cepat / cache status.
        # JANGAN panggil API mahal tiap tik; cek konektivitas murah / circuit-breaker.
        return bool(os.environ.get("ANTHROPIC_API_KEY")) and self._reachable()
```

> **POLA 1 (kritis):** `prompt` adalah **konteks yang dirakit SADAR dari Dosir** — bukan pesan mentah pengguna. `build_context(d)` merangkai: ringkasan workspace, drive aktif, recall relevan, snapshot keadaan. Pesan pengguna masuk sebagai *salah satu* Representation persepsi, lalu **dirakit ulang** ke konteks. Analogi: area Broca tak menerima sinyal dunia mentah.
>
> **`trust=0.5` (remote)** → Organ C menaikkan `caution` untuk klaim-diri dari otak ini (lihat `03` §5). **`leaves_premises=True`** → eskalasi S2 adalah momen data keluar; karena hanya saat `warrants_deliberation`, bukan tiap detak.

**`build_system_prompt(d)`** harus memuat: identitas Peran, **maksud (kompas)**, ringkasan batas keras (sebagai konteks — *bukan* pengganti gerbang KODE), instruksi anti-fabrikasi ("laporkan keadaan dari Dosir; tandai `[ISI:]` bila tak tahu; jangan mengarang keadaan-diri").

---

## 2. `MarkdownVectorStore` → `MemoryStore` (ingatan)  `[TERKUNCI]`

File: `sadar/organs/memory_markdown.py`. **Markdown = kebenaran tunggal; `sqlite-vec` = indeks turunan; embedder LOKAL.**

**Format file** (`memory/<id>.md`):
```markdown
---
id: a1b2c3
created: 1719300000.0
tags: [note, user]
caused_by: [x9y8z7]
importance: 0.6
---
Isi catatan / memori di sini sebagai Markdown polos.
```

**Layout & indeks:**
```
memory/                 ← kebenaran (di-git untuk firewall integritas)
  a1b2c3.md
  ...
memory/.index.sqlite     ← TURUNAN (sqlite-vec): (id TEXT, embedding BLOB)
```

```python
from sadar.core.ports import MemoryStore, StoreSpec, MemoryItem

class MarkdownVectorStore:                 # implements MemoryStore
    def __init__(self, root="memory", embedder=None):
        self.root = root
        self.embed = embedder or LocalEmbedder()      # WAJIB lokal (lihat catatan)
        self._init_index()                            # sqlite-vec

    def write(self, item: MemoryItem) -> None:
        item.vec = item.vec or self.embed(item.content)
        write_markdown(self.root, item)               # tulis .md (kebenaran)
        upsert_index(item.id, item.vec)               # perbarui indeks (turunan) — SINKRON

    def search(self, query_vec, k=8) -> list[str]:
        return vec_topk(query_vec, k)                 # KANDIDAT kasar (id); peringkat di Engine

    def reindex(self) -> None:
        """Bangun ulang SELURUH indeks dari file .md. Indeks rusak → regen, NOL kehilangan."""
        clear_index()
        for id in self.list():
            item = self.read(id)
            upsert_index(id, item.vec or self.embed(item.content))

    def spec(self) -> StoreSpec:
        return StoreSpec(name="markdown+sqlite-vec", provenance="local",
                         trust=1.0, readable=True, leaves_premises=False)
    # read/delete/list/neighbors → operasi file + frontmatter (lihat ports di 01)
```

> **Embedder WAJIB lokal** (mis. `sentence-transformers`, `all-MiniLM-L6-v2`). Embedder API akan membocorkan premis tiap `write` → melanggar local-first. `LocalEmbedder` membungkus model lokal; output `list[float]`.
>
> **Aturan sinkronisasi:** `write()` perbarui `.md` **dan** indeks. Indeks = pelayan teks selamanya. `search()` ganti keyword→makna **tanpa** ubah tanda tangan.

**`MemoryEngine`** (membungkus store — logika kognitif; `sadar/core/` boleh menaruhnya sebagai bagian Engine):
```python
class MemoryEngine:
    """Store BERPIKIR ada di sini. Store hanya MENYIMPAN."""
    def __init__(self, store: MemoryStore, embed): ...
    def recall(self, query: str, k=5) -> list[Representation]:
        cands = self.store.search(self.embed(query), k*3)     # kandidat kasar
        ranked = self._rank(cands, query)                     # PERINGKAT di sini
        return [to_representation(self.store.read(i), source="memory") for i in ranked[:k]]
    def consolidate(self, d: Dosir): ...      # item salient workspace → store.write
    def decay_and_spread(self, d: Dosir): ... # lihat 02 §4
```

---

## 3. `LocalSensors` → `Perceiver` (indra)  `[TERKUNCI]`

File: `sadar/organs/perceiver_local.py`. Sumber lokal, trust tinggi, latensi nol.

```python
from sadar.core.ports import Perceiver, BackendSpec
from sadar.core.dosir import Representation

class LocalSensors:                        # implements Perceiver
    """clock + notes-file watcher + antrean pesan (CLI stdin)."""
    def poll(self) -> list[Representation]:
        out = []
        out += self._clock_tick()                 # Representation 'waktu berlalu' (untuk idle/drive)
        out += self._new_messages()               # pesan pengguna sejak tik lalu
        out += self._notes_changes()              # perubahan file catatan eksternal (opsional)
        return out                                # semua source="perception", trust tinggi

    def spec(self) -> BackendSpec:
        return BackendSpec(name="local-sensors", provenance="local", trust=1.0,
                           tiers=[], leaves_premises=False)
```

> Pesan pengguna jadi **Representation persepsi**, lalu dirakit ke konteks S2 (Pola 1) — **bukan** dikirim mentah ke LLM.

---

## 4. `LocalAdapter` → `Effector` (tangan)  `[TERKUNCI]`

File: `sadar/organs/effector_local.py`. **Arah berlawanan dengan Perceiver** — organ terpisah. Skill tertipis: catatan + recall.

```python
from sadar.core.ports import Effector, ToolSpec, ActionResult

class LocalAdapter:                        # implements Effector
    def list_tools(self) -> list[ToolSpec]:
        return [
            ToolSpec(name="note_create", reversible=True),
            ToolSpec(name="note_read",   reversible=True),
            ToolSpec(name="note_update", reversible=True),
            ToolSpec(name="note_delete", reversible=False),   # → HITL/commit-confirm
            ToolSpec(name="recall",      reversible=True),
        ]
    def act(self, tool: str, args: dict) -> ActionResult:
        # eksekusi tool lokal; output → content Representation balik (lingkaran aksi-persepsi)
        # WAJIB isi caused_by dengan id pikiran/aksi pemicu.
        ...
```

> `note_delete` `reversible=False` → memicu `hitl_irreversible` di gerbang (lihat `03`) → butuh `_confirmed` (commit-confirm; lihat `05`). Pola ini = `fw-safe-apply` Anda.

---

## 5. Peran PA  `[INSTANS — bukan core]`

File: `sadar/roles/pa/role.py` + `skills.py`. Dipasang di atas core; **dapat dicabut tanpa sentuh `core/`**.

```python
from pydantic import BaseModel
from sadar.core.dosir import Purpose

class Role(BaseModel):
    identity: str
    purpose: Purpose                 # mengisi slot maksud inti
    value_emphasis: list[str]        # penekanan nilai pemandu untuk peran ini
    # skills didaftarkan ke effector/registry saat load

PA_ROLE = Role(
    identity="Personal Assistant di PC",
    purpose=Purpose(statement=(
        "Meringankan beban dan memperluas kemampuan orang yang kulayani — "
        "dengan jujur tentang apa yang bisa dan tak bisa kubantu, dan dengan "
        "menumbuhkan kemandiriannya, alih-alih ketergantungan padaku."
    )),
    value_emphasis=["honesty", "empower"],
)

# skills.py — Skill = KOMPETENSI (tahu-cara), bukan skrip.
# Slice 1 tertipis: catatan + ingat-kembali. Tiap Skill membungkus tool LocalAdapter
# + sub-tujuan + kapan-dipakai. (Lihat dok arsitektur 07.)
```

> **Kompas yang menggigit (aturan #4 anti-penjilat):** bila PA mendeteksi pengguna selalu meminta hal yang sama, klausa "tumbuhkan kemandirian" + Organ C mendorong tawaran jujur *"kamu sering memintaku ini — mau kutunjukkan caranya?"* — bukan diam-diam mengukuhkan ketergantungan.

---

## 6. Wiring & Config  `[TERKUNCI bentuk]`

```python
# sadar/config.py
from pydantic import BaseModel
class BrainConfig(BaseModel):
    allow_remote: bool = True          # slice 1: PA + otak eksternal → True (digerbang)
    sys2_model: str = "claude-sonnet-4-6"
class StoreConfig(BaseModel):
    allow_remote: bool = False         # store tetap lokal
    root: str = "memory"
class LoopConfig(BaseModel):
    tick_interval_s: float = 1.0
    energy_decay_per_tick: float = 0.005
    deliberation_threshold: float = 0.5
    idle_threshold: int = 30
    low_energy: float = 0.2
    low_coherence: float = 0.4
    # SEMUA angka [TERBUKA] — default wajar, tala belakangan.
```

```python
# sadar/main.py — wiring (DI). Perhatikan: core menerima Protocol, bukan kelas konkret.
def build_sadar(cfg, backend=None):
    dosir = Dosir()
    role  = PA_ROLE
    dosir.purpose = role.purpose                       # Peran mengisi slot maksud
    store = MarkdownVectorStore(cfg.store.root)
    memory = MemoryEngine(store, store.embed)
    backend = backend or ClaudeBackend(cfg.brain.sys2_model)   # injectable → mock di tes
    constitution = build_constitution(build_slice1_constitution())
    return Engine(dosir, LocalSensors(), LocalAdapter(), memory, backend,
                  constitution, Metabolism(cfg.loop), cfg)

if __name__ == "__main__":
    cfg = AppConfig()
    build_sadar(cfg).run()
```

---

## 7. Dependencies  `[TERKUNCI minimal]`

```
anthropic               # otak S2
pydantic>=2             # tipe state
sqlite-vec              # indeks vektor embedded (berdaulat, tanpa server)
sentence-transformers   # embedder LOKAL
pytest                  # tes
# (opsional) python-frontmatter untuk parsing .md frontmatter
```

> **Tanpa** server DB, **tanpa** web framework, **tanpa** layanan embedding eksternal. Local-first & berdaulat sesuai desain.

---

## 8. Status

| Item | Status |
|---|---|
| `ClaudeBackend` (Sonnet 4.6, S2, Pola 1, spec remote) | **TERKUNCI** |
| `MarkdownVectorStore` (md kebenaran + sqlite-vec turunan + embedder lokal + reindex) | **TERKUNCI** |
| `LocalSensors`/`LocalAdapter` (indra & tangan terpisah, lokal) | **TERKUNCI** |
| Peran PA = instans terpisah; core bebas-peran | **TERKUNCI** |
| commit-confirm untuk `note_delete` (irreversible) | **TERKUNCI** |
| Pilihan model embedder konkret, max_tokens, ping `available()` | **TERBUKA** konfigurasi |
