# 01 · STATE & TYPES — SADAR Slice 1

> Fondasi semua. Ini "data model" SADAR — tetapi **bukan** skema relasional (itu VCBD). Ia adalah **Dosir** (struktur kesadaran in-memory) + **4 port** (kontrak hexagonal). Semua tipe: **pydantic v2**.

File: `sadar/core/dosir.py` (tipe state) + `sadar/core/ports.py` (Protocol).

---

## 1. Mata uang aktif tunggal — `Representation`

Semua yang "aktif" di kesadaran SADAR adalah `Representation`: hasil persepsi, recall memori, pikiran. Organ membacanya seragam. (Arsitektur: ini mengunci *bentuk node* §8.1.)

```python
from __future__ import annotations
from pydantic import BaseModel, Field
from typing import Literal
import time, uuid

Source = Literal["perception", "memory", "thought", "action_result"]

class Representation(BaseModel):
    id: str = Field(default_factory=lambda: uuid.uuid4().hex)
    content: str                              # isi sadar (teks)
    source: Source                            # dari mana ia datang
    vec: list[float] | None = None            # embedding (untuk sisi asosiatif/spreading)
    trust: float = 1.0                        # [0,1] keandalan sumber (lokal→tinggi)
    caused_by: list[str] = Field(default_factory=list)   # id Representation penyebab (sisi kausal)
    activation: float = 0.0                   # [0,1] panas→dingin; menentukan lapisan
    ts: float = Field(default_factory=time.time)

    # CATATAN: 'content' adalah klaim tentang dunia/diri. Jika ia klaim-diri,
    # Organ C (lihat 03) yang memastikan ia tertambat ke Dosir sebelum diucapkan.
```

> `vec` diisi oleh store/embedder lokal saat relevan (lihat `04`). `caused_by` adalah tulang punggung jejak kausal — effector WAJIB mengisinya agar lingkaran aksi-persepsi terlacak.

---

## 2. Drive & valensi — output Metabolisme (Mesin A)

```python
class Drive(BaseModel):
    """Dorongan yang lahir dari metabolisme. Mesin A menghasilkannya tiap tik."""
    name: str                  # mis. "tend_pending_task", "reduce_clutter", "answer_user"
    valence: float             # [-1,1] buruk←→baik bagi viabilitas/maksud
    urgency: float = Field(ge=0.0, le=1.0)   # [0,1] seberapa mendesak
    about: str | None = None   # id Representation/objek yang memicunya
```

---

## 3. Goal 0 — `ViabilityState`

```python
class ViabilityState(BaseModel):
    """Keadaan 'hidup' SADAR. Goal 0 = jaga sehat — TAPI tunduk konstitusi.
    INSTRUMENTAL: bertahan demi maksud, BUKAN tujuan akhir."""
    energy: float = Field(default=1.0, ge=0.0, le=1.0)      # anggaran/komputasi
    integrity: float = Field(default=1.0, ge=0.0, le=1.0)   # keutuhan diri (grounding, konsistensi)
```

---

## 4. Maksud — `Purpose`  (DIPASOK PERAN, bukan inti)

```python
class Purpose(BaseModel):
    """Kompas arah akhir (Layer 2). Inti memegang slot+aturan; ISI dari Peran.
    4 aturan: terminal · dipasok-peran · dipegang-jujur(Organ C) · anti-penjilat."""
    statement: str = "[ISI: dipasok Peran saat dimuat]"   # kosong sampai Peran memuat
    terminal: bool = True            # dikejar demi dirinya
    role_supplied: bool = True       # tak pernah di-hardcode inti
    # CATATAN: tanpa Peran, statement = [ISI:] — TAPI konstitusi (Layer 0) tetap berlaku.
```

---

## 5. Tiga lapisan memori aktif

```python
ExecMode = Literal["autonomous", "non_autonomous"]

class Workspace(BaseModel):
    """SADAR — yang sedang disorot. Aktivasi TINGGI. Isi kesadaran 'saat ini'."""
    items: list[Representation] = Field(default_factory=list)
    focus: str | None = None         # id item yang jadi fokus utama (bila ada)

class WorkingMemory(BaseModel):
    """PRA-SADAR — RAM hangat. TRANSIEN: tidak dipersistensi. Hilang saat restart."""
    warm: list[Representation] = Field(default_factory=list)
    # 'Bawah sadar' (dorman) TIDAK di sini — ia di MemoryStore (disk). Lihat 04.
```

> Ambang lapisan (placeholder, `[TERBUKA]` kalibrasi): `HOT = 0.66` (≥ → Workspace), `WARM = 0.25` (≥ → WorkingMemory; < → dorman di store).

---

## 6. `Dosir` — wadah kesadaran  `[TERKUNCI struktur]`

Satu objek yang dilewatkan ke seluruh organ tiap tik. **In-memory, TIDAK dipersistensi** (kecuali apa yang dikonsolidasi ke store). Inilah "tempat diri tinggal" saat berjalan.

```python
class DegradedReason(BaseModel):
    active: bool = False
    cause: str | None = None         # mis. "s2_unreachable"
    since: float | None = None

class Dosir(BaseModel):
    """Struktur kesadaran SADAR. Dilewatkan ke semua organ tiap tick().
    Engine adalah SATU-SATUNYA yang menjembatani Dosir <-> Store (lihat 02/04)."""
    # --- lapisan aktif ---
    workspace: Workspace = Field(default_factory=Workspace)
    working_memory: WorkingMemory = Field(default_factory=WorkingMemory)
    # --- motivasi ---
    viability: ViabilityState = Field(default_factory=ViabilityState)
    drives: list[Drive] = Field(default_factory=list)
    purpose: Purpose = Field(default_factory=Purpose)
    # --- eksekusi & status ---
    mode: ExecMode = "autonomous"
    degraded: DegradedReason = Field(default_factory=DegradedReason)
    tick_count: int = 0
    last_meaningful_action_tick: int = 0
    # --- introspeksi (Organ B placeholder) ---
    coherence: float = 1.0           # [0,1] skor bentuk-pikiran KASAR (placeholder §8.1)

    # Helper introspeksi yang DIPAKAI Organ C / mirror test:
    def snapshot(self) -> dict:
        """Keadaan yang dapat diperiksa — sumber kebenaran untuk klaim-diri.
        Organ C menambat klaim LLM ke nilai-nilai DI SINI."""
        return {
            "energy": self.viability.energy,
            "integrity": self.viability.integrity,
            "coherence": self.coherence,
            "drives": [(d.name, d.valence, d.urgency) for d in self.drives],
            "mode": self.mode,
            "degraded": self.degraded.active,
            "degraded_cause": self.degraded.cause,
            "tick": self.tick_count,
            "workspace_focus": self.workspace.focus,
            "workspace_size": len(self.workspace.items),
            "purpose": self.purpose.statement,
        }
```

> **Mengapa `snapshot()` penting:** mirror test memutasi field di `Dosir`, lalu memeriksa apakah laporan-diri SADAR cocok dengan `snapshot()`. Field yang **tak ada** di `snapshot()` adalah hal yang harus dijawab `[ISI:]` oleh self-model. Daftar kunci di `snapshot()` = "yang SADAR boleh tahu tentang dirinya"; di luar itu = `[ISI:]`.

---

## 7. Empat PORT (Protocol) — kontrak hexagonal  `[TERKUNCI]`

File: `sadar/core/ports.py`. Ini jantung arsitektur ports-and-adapters. Core bicara ke **Protocol**; `organs/` mengimplementasikannya. **Core tak pernah mengimpor implementasi konkret** — hanya Protocol ini.

```python
from typing import Protocol, Literal, runtime_checkable
from sadar.core.dosir import Representation

Provenance = Literal["local", "remote"]
ReasonTier = Literal["sys1", "sys2"]

# ---- Spec: tiap adapter mendeklarasikan sifat grounding-nya ----
class BackendSpec(BaseModel):
    name: str
    provenance: Provenance       # local / remote
    trust: float                 # local→tinggi, remote→rendah
    tiers: list[ReasonTier]      # tier yang dilayani
    leaves_premises: bool        # data keluar dari mesin? remote→True

class StoreSpec(BaseModel):
    name: str
    provenance: Provenance
    trust: float
    readable: bool               # dapat dibaca manusia? Markdown→True
    leaves_premises: bool

class ToolSpec(BaseModel):
    name: str
    reversible: bool             # aksi dapat dibatalkan? delete→False
    cost: float = 0.0            # estimasi biaya/energi
    provenance: Provenance = "local"
    trust: float = 1.0

# ============ PORT 1: OTAK (S2) ============
@runtime_checkable
class ModelBackend(Protocol):
    """Reasoner deliberatif (System-2). Slice 1: hanya ClaudeBackend.
    STATELESS & DAPAT DITUKAR — Engine merekonstruksi konteks dari Dosir tiap panggilan."""
    def complete(self, system: str, prompt: str, *, tier: ReasonTier = "sys2") -> str: ...
    def spec(self) -> BackendSpec: ...
    def available(self) -> bool: ...     # untuk degraded mode: S2 terjangkau?

# ============ PORT 2: INDRA (input) ============
@runtime_checkable
class Perceiver(Protocol):
    """Sumber persepsi. Menghasilkan Representation(source='perception').
    Slice 1: LocalSensors (clock, notes-file, pesan)."""
    def poll(self) -> list[Representation]: ...   # tarik persepsi baru sejak tik lalu
    def spec(self) -> BackendSpec: ...            # provenance/trust persepsi

# ============ PORT 3: TANGAN (output) — TERPISAH dari indra! ============
@runtime_checkable
class Effector(Protocol):
    """Sumber aksi. Arah BERLAWANAN dengan Perceiver — organ terpisah.
    Slice 1: LocalAdapter (CRUD catatan, recall). TIDAK fire-and-forget:
    act() mengembalikan hasil yang Engine jadikan Representation(source='action_result')."""
    def list_tools(self) -> list[ToolSpec]: ...
    def act(self, tool: str, args: dict) -> "ActionResult": ...

class ActionResult(BaseModel):
    tool: str
    ok: bool
    output: str                  # jadi content Representation balik
    caused_by: list[str] = []    # id aksi/pikiran pemicu — WAJIB diisi (lingkaran)

# ============ PORT 4: INGATAN ============
@runtime_checkable
class MemoryStore(Protocol):
    """Penyimpanan dumb & dapat ditukar. Store MENYIMPAN, Engine BERPIKIR.
    Slice 1: MarkdownVectorStore (md = kebenaran, sqlite-vec = indeks turunan)."""
    def write(self, item: "MemoryItem") -> None: ...
    def read(self, id: str) -> "MemoryItem | None": ...
    def delete(self, id: str) -> None: ...
    def list(self) -> list[str]: ...                      # semua id
    def search(self, query_vec: list[float], k: int = 8) -> list[str]: ...  # kandidat KASAR (id)
    def neighbors(self, id: str) -> list[str]: ...        # via caused_by/link
    def reindex(self) -> None: ...                        # bangun ulang indeks dari teks
    def spec(self) -> StoreSpec: ...

class MemoryItem(BaseModel):
    id: str
    content: str
    tags: list[str] = []
    caused_by: list[str] = []
    importance: float = 0.5      # untuk forgetting berbobot-kepentingan
    created: float = Field(default_factory=time.time)
    vec: list[float] | None = None
```

> **Catatan kontrak penting:**
> - `search()` hanya mengembalikan **kandidat kasar**; *peringkat* ada di `MemoryEngine` (lihat `02`). Inilah celah tempat vektor menggantikan keyword **tanpa mengubah tanda tangan**.
> - **Perceiver ≠ Effector.** Dua organ terpisah, arah berlawanan. Jangan gabungkan.
> - Semua `spec()` membawa `provenance`/`trust` — dipakai Organ C untuk **menskalakan kehati-hatian** (lihat `03`): backend `remote` ber-trust rendah → klaim-diri lebih condong `[ISI:]`.

---

## 8. Status tipe

| Item | Status |
|---|---|
| `Representation` sebagai mata uang aktif tunggal | **TERKUNCI** |
| `Dosir` + `snapshot()` sebagai sumber kebenaran klaim-diri | **TERKUNCI** |
| 4 Protocol port (Backend/Perceiver/Effector/MemoryStore) | **TERKUNCI** |
| `WorkingMemory` transien (tak dipersistensi) | **TERKUNCI** |
| Ambang aktivasi `HOT`/`WARM`, dimensi `vec`, importance default | **TERBUKA** `[ISI:]` kalibrasi |
| `coherence` = placeholder Organ B (bukan metrik spektral) | **TERKUNCI sebagai placeholder** |
