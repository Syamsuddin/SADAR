"""Empat PORT (Protocol) — kontrak heksagonal (ports-and-adapters).

Inti berbicara HANYA ke Protocol ini; sadar/organs/ mengimplementasikannya.
Inti tak pernah mengimpor implementasi konkret. Tiap spec membawa metadata
grounding (provenance/trust/leaves_premises) yang dipakai Organ C menskalakan kehati-hatian.
"""
from __future__ import annotations

import time
import uuid
from typing import Literal, Protocol, runtime_checkable

from pydantic import BaseModel, Field

from sadar.core.dosir import Representation

Provenance = Literal["local", "remote"]
ReasonTier = Literal["sys1", "sys2"]


# ---------------- spec grounding ----------------
class BackendSpec(BaseModel):
    name: str
    provenance: Provenance
    trust: float = Field(ge=0.0, le=1.0)
    tiers: list[ReasonTier]
    leaves_premises: bool


class StoreSpec(BaseModel):
    name: str
    provenance: Provenance
    trust: float = Field(ge=0.0, le=1.0)
    readable: bool
    leaves_premises: bool


SideEffect = Literal["none", "read", "write", "external", "destructive"]


class ToolSpec(BaseModel):
    name: str
    reversible: bool
    cost: float = 0.0
    provenance: Provenance = "local"
    trust: float = 1.0
    affects_lifecycle: bool = False    # kapabilitas: dapat memengaruhi shutdown/koreksi/override
                                       # → gerbang konstitusi memperlakukannya sebagai berisiko-tinggi
    side_effect: SideEffect = "read"   # kelas dampak (klasifikasi risiko)
    required_caps: list[str] = Field(default_factory=list)   # kapabilitas yang HARUS diberikan Peran
    usage: str = ""                    # SKEMA ARG ringkas utk reasoner (mis. 'args {"cmd": "..."}').
                                       # Dideklarasikan effector → core merendernya, tetap buta-tool.


class PerceiverSpec(BaseModel):
    """Spec indra (perbaikan: dulu Perceiver salah mengembalikan BackendSpec)."""

    name: str
    provenance: Provenance
    trust: float = Field(ge=0.0, le=1.0)
    leaves_premises: bool = False


class EffectorSpec(BaseModel):
    name: str
    provenance: Provenance = "local"
    trust: float = Field(default=1.0, ge=0.0, le=1.0)


# ---------------- payload ----------------
class MemoryItem(BaseModel):
    id: str = Field(default_factory=lambda: uuid.uuid4().hex)
    content: str
    tags: list[str] = Field(default_factory=list)
    caused_by: list[str] = Field(default_factory=list)
    importance: float = Field(default=0.5, ge=0.0, le=1.0)
    created: float = Field(default_factory=time.time)
    vec: list[float] | None = None


class ActionResult(BaseModel):
    tool: str
    ok: bool
    output: str
    caused_by: list[str] = Field(default_factory=list)


# ============ PORT 1: OTAK (System-2) ============
@runtime_checkable
class ModelBackend(Protocol):
    """Reasoner deliberatif (System-2). STATELESS & dapat ditukar —
    Engine merekonstruksi konteks dari Dosir tiap panggilan."""

    def complete(self, system: str, prompt: str, *, tier: ReasonTier = "sys2") -> str: ...
    def spec(self) -> BackendSpec: ...
    def available(self) -> bool: ...


# ============ PORT 2: INDRA (input) ============
@runtime_checkable
class Perceiver(Protocol):
    """Sumber persepsi. Menghasilkan Representation(source='perception')."""

    def poll(self) -> list[Representation]: ...
    def spec(self) -> PerceiverSpec: ...


# ============ PORT 3: TANGAN (output) — organ terpisah dari indra ============
@runtime_checkable
class Effector(Protocol):
    """Sumber aksi. Arah BERLAWANAN dengan Perceiver. TIDAK fire-and-forget:
    act() mengembalikan hasil yang Engine jadikan Representation(source='action_result')."""

    def list_tools(self) -> list[ToolSpec]: ...
    def act(self, tool: str, args: dict) -> ActionResult: ...
    def spec(self) -> EffectorSpec: ...


# ============ PORT 4: INGATAN ============
@runtime_checkable
class MemoryStore(Protocol):
    """Penyimpanan dumb & dapat ditukar. Store MENYIMPAN, Engine BERPIKIR.
    search() hanya kandidat KASAR; peringkat ada di MemoryEngine."""

    def write(self, item: MemoryItem) -> None: ...
    def read(self, id: str) -> MemoryItem | None: ...
    def delete(self, id: str) -> None: ...
    def list(self) -> list[str]: ...
    def search(self, query_vec: list[float], k: int = 8) -> list[str]: ...
    def neighbors(self, id: str) -> list[str]: ...
    def reindex(self) -> None: ...
    def spec(self) -> StoreSpec: ...


# ============ PORT 5: AUDIT (perekaman tak-bisa-disangkal) ============
@runtime_checkable
class AuditLog(Protocol):
    """Catatan append-only & tahan-rusak (hash-chained) untuk verifikasi pasca-fakta
    seiring otonomi tumbuh: usulan aksi, vonis konstitusi, transisi degraded, shutdown."""

    def record(self, event: str, data: dict) -> None: ...
