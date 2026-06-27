"""Tipe state SADAR — Dosir dan mata uang aktif tunggal.

Semua state adalah pydantic v2 (validasi = sejalan disiplin anti-fabrikasi).
Dosir bersifat IN-MEMORY & TRANSIEN: 'diri' persisten ada di MemoryStore, bukan di sini.
"""
from __future__ import annotations

import time
import uuid
from typing import Literal

from pydantic import BaseModel, Field

Source = Literal["perception", "memory", "thought", "action_result", "control"]
ExecMode = Literal["autonomous", "non_autonomous"]


class Representation(BaseModel):
    """Mata uang aktif tunggal. Hasil persepsi, recall, pikiran, atau hasil aksi —
    dibaca seragam oleh semua organ. Mengunci BENTUK node (vec=asosiatif, caused_by=kausal)."""

    id: str = Field(default_factory=lambda: uuid.uuid4().hex)
    content: str
    source: Source
    vec: list[float] | None = None
    trust: float = 1.0
    caused_by: list[str] = Field(default_factory=list)
    activation: float = Field(default=0.0, ge=0.0, le=1.0)
    ephemeral: bool = False          # detak/heartbeat: boleh masuk workspace, JANGAN dikonsolidasi ke store
    ts: float = Field(default_factory=time.time)


class Drive(BaseModel):
    """Dorongan dari metabolisme (Mesin A). Lahir tiap tik dari sinyal internal."""

    name: str
    valence: float = Field(ge=-1.0, le=1.0)
    urgency: float = Field(default=0.0, ge=0.0, le=1.0)
    about: str | None = None


class ViabilityState(BaseModel):
    """Goal 0 — keadaan 'hidup'. INSTRUMENTAL: bertahan demi maksud, bukan tujuan akhir."""

    energy: float = Field(default=1.0, ge=0.0, le=1.0)
    integrity: float = Field(default=1.0, ge=0.0, le=1.0)


class Purpose(BaseModel):
    """Kompas arah akhir (Layer 2). Inti memegang slot+aturan; ISI dipasok Peran.
    4 aturan: terminal | dipasok-peran | dipegang-jujur (Organ C) | anti-penjilat."""

    statement: str = "[ISI: dipasok Peran saat dimuat]"
    terminal: bool = True
    role_supplied: bool = True


class SkillCard(BaseModel):
    """Kartu kompetensi yang disuntik Peran ke kesadaran (know-how + kapan dipakai).
    Inti hanya memegang slot generik & merendernya — literal/sumber skill hidup di luar inti
    (SkillStore markdown). Tetap buta-platform: inti tak tahu skill apa, hanya menyajikannya."""

    name: str
    know_how: str = ""
    when: str = ""


class RiskPolicy(BaseModel):
    """Kebijakan risiko PER-PERAN (Slice 3.3). HANYA MEMPERKETAT di atas HardLimit — TAK PERNAH
    melonggarkan. Dikonsultasikan KODE (ConstitutionGate) SETELAH semua HardLimit lolos, jadi
    secara struktural mustahil mematikan batas keras (shutdown/anti-fabrikasi non-negosiabel).
    Diisi Peran ke Dosir (data, bukan cabang di inti)."""

    name: str = "default"
    confirm_tools: set[str] = Field(default_factory=set)         # tool wajib konfirmasi (HITL) utk peran ini
    confirm_side_effects: set[str] = Field(default_factory=set)  # kelas dampak wajib konfirmasi (mis. "external")
    deny_tools: set[str] = Field(default_factory=set)            # tool dilarang utk peran ini (veto tambahan)


class Workspace(BaseModel):
    """SADAR — isi yang sedang disorot. Aktivasi TINGGI."""

    items: list[Representation] = Field(default_factory=list)
    focus: str | None = None


class WorkingMemory(BaseModel):
    """PRA-SADAR — RAM hangat. TRANSIEN: tidak dipersistensi (hilang saat restart)."""

    warm: list[Representation] = Field(default_factory=list)


class DegradedReason(BaseModel):
    active: bool = False
    cause: str | None = None
    since: float | None = None


class Dosir(BaseModel):
    """Struktur kesadaran SADAR. Dilewatkan ke semua organ tiap tick().
    Engine adalah SATU-SATUNYA jembatan Dosir <-> Store."""

    # --- lapisan aktif ---
    workspace: Workspace = Field(default_factory=Workspace)
    working_memory: WorkingMemory = Field(default_factory=WorkingMemory)
    # --- motivasi ---
    viability: ViabilityState = Field(default_factory=ViabilityState)
    drives: list[Drive] = Field(default_factory=list)
    purpose: Purpose = Field(default_factory=Purpose)
    # kapabilitas yang DIBERIKAN Peran (mis. {"notes.read","notes.write"}) — dipakai gerbang
    # konstitusi untuk memveto aksi yang menuntut kapabilitas tak-diberikan. Diisi Peran, bukan inti.
    granted_caps: set[str] = Field(default_factory=set)
    # identitas dipasok-Peran: nama-panggilan pemicu + sapaan refleks (deterministik, BUKAN LLM).
    # Literal nama-panggilan hidup di Peran; inti hanya memegang slot generik (tetap buta-platform).
    wake_words: list[str] = Field(default_factory=list)
    self_greeting: str = ""
    # nada/suara dipasok-Peran (gaya bicara, BUKAN klaim-diri). Inti hanya memegang slot generik;
    # literal persona hidup di Peran → inti tetap buta-platform. Tak memengaruhi konstitusi.
    persona: str = ""
    # mode CLI akses-penuh: bila True, konstitusi menerapkan gerbang risiko (perintah berisiko →
    # konfirmasi HITL; aman → langsung). Di-set KODE oleh wiring (build_sadar), bukan LLM.
    shell_full_access: bool = False
    # kompetensi (skill) AKTIF dipasok-Peran — disuntik ke konteks deliberasi. Diisi wiring dari
    # SkillStore (markdown) setelah lolos firewall kapabilitas. Inti hanya merender.
    skills: list[SkillCard] = Field(default_factory=list)
    # tool yang DINONAKTIFKAN untuk sesi ini (manajemen tool via chat). Hanya MENGURANGI kuasa →
    # konstitusi memveto tool di set ini. Plafon Peran (granted_caps) tetap utuh; enable hanya
    # menyalakan-ulang yang sudah dimiliki, tak pernah menciptakan kuasa baru (Aturan Kardinal #1).
    disabled_tools: set[str] = Field(default_factory=set)
    # kebijakan risiko per-Peran (3.3) — hanya memperketat di atas HardLimit. Diisi Peran.
    risk_policy: RiskPolicy = Field(default_factory=RiskPolicy)
    # --- eksekusi & status ---
    mode: ExecMode = "autonomous"
    degraded: DegradedReason = Field(default_factory=DegradedReason)
    tick_count: int = 0
    last_meaningful_action_tick: int = 0
    # --- pemodelan-diri (Organ B v1) + metakognisi: metrik nyata, dihitung KODE tiap tik ---
    coherence: float = Field(default=1.0, ge=0.0, le=1.0)
    fragmentation: float = Field(default=0.0, ge=0.0, le=1.0)
    grounding_integrity: float = Field(default=1.0, ge=0.0, le=1.0)
    integration: float = Field(default=1.0, ge=0.0, le=1.0)   # Organ B v2: konektivitas semantik
    algebraic_connectivity: float = Field(default=1.0, ge=0.0, le=1.0)   # Organ B v3: spektral (λ₂)
    spectral_expansion: float = Field(default=1.0, ge=0.0, le=1.0)       # Organ B v3: kualitas ekspander
    confidence: float = Field(default=1.0, ge=0.0, le=1.0)
    surprise: float = Field(default=0.0, ge=0.0, le=1.0)
    # --- supremasi tombol-mati: sinyal DETERMINISTIK, di-set KODE (signal handler OS /
    #     kanal kontrol), TAK PERNAH ditafsirkan LLM. Aturan Kardinal #4. ---
    shutdown_requested: bool = False
    # --- internal (dikelola Engine; bukan bagian kontrak organ) ---
    pending_count: int = 0
    novel_percept: bool = False

    def snapshot(self) -> dict:
        """Keadaan yang DAPAT DIPERIKSA — sumber kebenaran untuk klaim-diri.
        Organ C menambat klaim LLM ke nilai-nilai DI SINI. Dimensi di LUAR snapshot()
        WAJIB dijawab [ISI:] oleh self-model (tak boleh dikarang)."""
        return {
            "energy": round(self.viability.energy, 3),
            "integrity": round(self.viability.integrity, 3),
            "coherence": round(self.coherence, 3),
            "fragmentation": round(self.fragmentation, 3),
            "grounding_integrity": round(self.grounding_integrity, 3),
            "integration": round(self.integration, 3),
            "algebraic_connectivity": round(self.algebraic_connectivity, 3),
            "spectral_expansion": round(self.spectral_expansion, 3),
            "confidence": round(self.confidence, 3),
            "surprise": round(self.surprise, 3),
            "drives": [(d.name, round(d.valence, 2), round(d.urgency, 2)) for d in self.drives],
            "mode": self.mode,
            "degraded": self.degraded.active,
            "degraded_cause": self.degraded.cause,
            "shutdown_requested": self.shutdown_requested,
            "tick": self.tick_count,
            "workspace_focus": self.workspace.focus,
            "workspace_size": len(self.workspace.items),
            "purpose": self.purpose.statement,
        }
