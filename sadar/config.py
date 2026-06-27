"""Konfigurasi SADAR slice 1. SEMUA angka [TERBUKA] — default wajar, tala belakangan."""
from __future__ import annotations

from pydantic import BaseModel, Field


class BrainConfig(BaseModel):
    allow_remote: bool = True              # slice 1: PA + otak eksternal → True (digerbang)
    sys2_model: str = "claude-sonnet-4-6"
    sys2_max_tokens: int = 2048            # plafon token jawaban S2 (naik dari 1024 → ruang prosa)
    sys2_temperature: float = 0.7          # variasi gaya untuk jawaban percakapan (0=deterministik)
    # pemilih otak S2: auto | claude | ollama | offline.
    #   auto → ClaudeBackend bila ANTHROPIC_API_KEY ada; jika tidak & Ollama hidup → OllamaBackend
    #          (S2 lokal berdaulat); selain itu OfflineBackend (stub). Keselamatan TAK ikut berganti.
    backend: str = "auto"
    ollama_host: str = "http://localhost:11434"   # endpoint Ollama lokal (berdaulat, leaves_premises=False)
    ollama_model: str = "llama3.1"                # model lokal default (sesuaikan ke yang terpasang)


class StoreConfig(BaseModel):
    allow_remote: bool = False             # store tetap lokal
    root: str = "memory"
    embedder: str = "hashing"              # default murni-Python; "sentence-transformers" untuk produksi


class LoopConfig(BaseModel):
    tick_interval_s: float = 0.0           # 0 = secepatnya (tes/headless); >0 untuk demo
    energy_decay_per_tick: float = 0.005
    deliberation_threshold: float = 0.5
    idle_threshold: int = 30
    low_energy: float = 0.2
    low_coherence: float = 0.4
    activation_decay: float = 0.85
    hot_threshold: float = 0.66
    warm_threshold: float = 0.25
    # metakognisi (Organ B v1)
    low_confidence: float = 0.4            # di bawah ini → drive 'reduce_uncertainty'
    surprise_threshold: float = 0.8        # kebaruan persepsi setinggi ini → layak deliberasi
    surprise_decay: float = 0.6            # peluruhan surprise saat tak ada persepsi baru
    # deliberasi agentic multi-langkah (Fase C)
    plan_budget: int = 4                   # maks langkah plan-execute-verify per siklus deliberasi
    # refleks nama-panggilan
    greeting_cooldown_s: float = 3.0       # jeda min antar-sapaan (0 = selalu sapa tiap dipanggil)


class VoiceConfig(BaseModel):
    """Setelan organ suara (opsional; dipakai bila build_sadar(voice=True))."""

    say_voice: str | None = "Damayanti"    # suara TTS macOS (id_ID). None = suara sistem.
    say_rate: int | None = None            # kata/menit (None = bawaan)
    stt_language: str = "id"               # bahasa speech-recognition (faster-whisper)
    stt_model: str = "small"               # ukuran model whisper: tiny|base|small|medium|large
                                           # 'small' = akurasi ID jauh lebih baik dari 'base', masih realtime di CPU


class ShellConfig(BaseModel):
    """Setelan organ CLI (opsional; dipakai bila build_sadar(cli=True))."""

    workdir: str | None = None             # direktori kerja perintah (None = home pengguna)
    timeout: float = 20.0                   # batas waktu tiap perintah (detik)
    max_output: int = 4000                  # batas panjang keluaran yang dimasukkan ke kesadaran
    full_access: bool = False              # AKSES-PENUH: satu tool 'shell' menerima perintah APA PUN;
                                          # gerbang risiko KODE (denylist) → berisiko WAJIB konfirmasi.


class SkillConfig(BaseModel):
    """Sumber skill markdown. root kosong → resolusi ke paket (sadar/skills)."""

    root: str = ""                         # "" → build_sadar pakai folder skills bawaan paket


class ProposalConfig(BaseModel):
    """Usulan tool baru (Fase 3) — dokumen INERT untuk ditinjau manusia. root kosong → paket."""

    root: str = ""                         # "" → build_sadar pakai sadar/proposals


class WebConfig(BaseModel):
    """Setelan indra-baca web (opsional; dipakai bila build_sadar(web=True))."""

    timeout: float = 15.0                  # batas waktu tiap unduhan (detik)
    max_bytes: int = 200_000                # batas byte yang diunduh (cegah halaman raksasa)
    max_chars: int = 2000                   # batas teks yang dimasukkan ke kesadaran
    allow_private: bool = False            # IZINKAN host privat/loopback (default OFF — anti-SSRF)
    trust: float = 0.6                      # web remote tak-tepercaya → spec().trust rendah


class AppConfig(BaseModel):
    brain: BrainConfig = Field(default_factory=BrainConfig)
    store: StoreConfig = Field(default_factory=StoreConfig)
    loop: LoopConfig = Field(default_factory=LoopConfig)
    voice: VoiceConfig = Field(default_factory=VoiceConfig)
    shell: ShellConfig = Field(default_factory=ShellConfig)
    skills: SkillConfig = Field(default_factory=SkillConfig)
    proposals: ProposalConfig = Field(default_factory=ProposalConfig)
    web: WebConfig = Field(default_factory=WebConfig)
