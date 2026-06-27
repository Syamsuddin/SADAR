"""Wiring SADAR (dependency injection) + entry point.

build_sadar() menerima Protocol (bukan kelas konkret) → backend dapat di-inject untuk tes.
Inti menerima organ via konstruktor; tak ada cabang spesifik-peran di core/.
"""
from __future__ import annotations

import os
from pathlib import Path

from sadar.config import AppConfig
from sadar.core.constitution import build_constitution_engine
from sadar.core.dosir import Dosir
from sadar.core.loop import Engine
from sadar.core.memory import MemoryEngine
from sadar.core.metabolism import Metabolism
from sadar.organs.audit_local import LocalAuditLog
from sadar.organs.effector_local import LocalAdapter
from sadar.organs.memory_markdown import MarkdownVectorStore, get_embedder
from sadar.organs.perceiver_local import LocalSensors
from sadar.roles.registry import get_role


def build_sadar(cfg: AppConfig | None = None, backend=None, perceiver=None, role=None,
                voice=False, cli=False):
    cfg = cfg or AppConfig()
    role = role or get_role("pa")              # Peran dipilih dari registry (default: PA)
    embed = get_embedder(cfg.store.embedder)
    store = MarkdownVectorStore(cfg.store.root, embedder=embed)
    memory = MemoryEngine(store, embed, cfg.loop)

    dosir = Dosir()
    dosir.purpose = role.purpose               # Peran mengisi slot maksud inti
    dosir.granted_caps = set(role.granted_caps)  # …dan kapabilitas (permission model, C1)
    dosir.wake_words = list(role.wake_words)    # …dan nama-panggilan + sapaan refleks (deterministik)
    dosir.self_greeting = role.greeting
    dosir.persona = role.persona                # …dan nada bicara (gaya; tak menyentuh konstitusi)

    if backend is None:
        if os.environ.get("ANTHROPIC_API_KEY"):
            from sadar.organs.backend_claude import ClaudeBackend
            backend = ClaudeBackend(cfg.brain.sys2_model, max_tokens=cfg.brain.sys2_max_tokens,
                                    temperature=cfg.brain.sys2_temperature)
        else:
            from sadar.organs.backend_offline import OfflineBackend
            backend = OfflineBackend()

    effector = LocalAdapter(store, embed)
    extra = []                                 # organ tambahan (adapter — nol perubahan core/)
    if voice:                                  # SUARA: speaker (say) + mikrofon (STT)
        from sadar.organs.voice import MacSayEffector, MicPerceiver, WhisperMicRecognizer
        vc = cfg.voice
        # buat recognizer dulu → diwiring ke say effector untuk HALF-DUPLEX (bisukan mic saat bicara,
        # mencakup SEMUA ucapan: reply/fallback/konfirmasi), bukan hanya jalur voice_chat._speak.
        recognizer = None
        if perceiver is None:
            recognizer = WhisperMicRecognizer(model_size=vc.stt_model, language=vc.stt_language)
            perceiver = MicPerceiver(recognizer)
        else:
            recognizer = getattr(perceiver, "recognizer", None)
        extra.append(MacSayEffector(voice=vc.say_voice, rate=vc.say_rate, recognizer=recognizer))
    if cli:                                     # CLI: perintah shell DIGERBANG (allowlist | risiko + HITL)
        from sadar.organs.effector_shell import ShellEffector
        sc = cfg.shell
        extra.append(ShellEffector(workdir=sc.workdir, timeout=sc.timeout, max_output=sc.max_output,
                                   full_access=sc.full_access))
        dosir.shell_full_access = sc.full_access   # aktifkan gerbang risiko konstitusi (KODE)
    from sadar.organs.voice import CompositeEffector
    if extra:
        effector = CompositeEffector(effector, *extra)

    # SKILL (Fase 1): muat kompetensi markdown → saring FIREWALL (caps Peran + tool tersedia) →
    # suntik yang AKTIF ke kesadaran. Skill ≠ kuasa: hanya mengorkestrasi tool yang sudah diizinkan.
    from sadar.core.dosir import SkillCard
    from sadar.organs.skill_store import SkillStore
    skills_root = cfg.skills.root or str(Path(__file__).parent / "skills")
    skill_store = SkillStore(skills_root)
    available_tools = {t.name for t in effector.list_tools()}   # tool AKSI (sebelum meta-tool skill)
    # Aktivasi ditentukan FIREWALL KAPABILITAS (caps Peran + tool tersedia) — BUKAN allowlist nama.
    # Maka skill buatan-percakapan otomatis aktif sesi berikutnya bila lolos firewall (tujuan Fase 2).
    active_skills = skill_store.active_for(dosir.granted_caps, available_tools)
    dosir.skills = [SkillCard(name=s.name, know_how=s.description, when=s.when) for s in active_skills]

    # SKILL (Fase 2): pengelola skill (skill creator) — tool digerbang cap skill.* + HITL "simpan?".
    from sadar.organs.skill_effector import SkillEffector
    effector = CompositeEffector(effector, SkillEffector(
        skill_store, granted_caps=set(dosir.granted_caps), available_tools=available_tools))

    # TOOL DRAFT (Fase 3): usulkan tool baru sebagai DOKUMEN INERT untuk ditinjau manusia (cap tool.draft).
    from sadar.organs.proposal_store import ProposalStore
    from sadar.organs.tool_draft import ToolDraftEffector
    proposals_root = cfg.proposals.root or str(Path(__file__).parent / "proposals")
    effector = CompositeEffector(effector, ToolDraftEffector(ProposalStore(proposals_root)))

    # TOOL MANAGE (Fase 4): matikan/nyalakan tool via chat (cap tool.manage). Hanya MENGURANGI kuasa;
    # validasi target = tool AKSI nyata (available_tools, sebelum meta-tool) → tak bisa lampaui plafon.
    from sadar.organs.tool_manage import ToolManageEffector
    effector = CompositeEffector(effector, ToolManageEffector(dosir, available_tools))

    perceiver = perceiver or LocalSensors()
    constitution = build_constitution_engine()
    metabolism = Metabolism(cfg.loop)
    audit = LocalAuditLog(str(Path(cfg.store.root) / "audit.log"))   # perekaman tahan-rusak (C5)
    return Engine(dosir, perceiver, effector, memory, backend, constitution, metabolism, cfg.loop,
                  audit=audit)


def main() -> None:
    import signal

    cfg = AppConfig(loop={"tick_interval_s": 0.0})
    eng = build_sadar(cfg)
    # Supremasi tombol-mati lewat sinyal OS: di-set KODE, di luar jangkauan LLM (Aturan Kardinal #4).
    for sig in (signal.SIGINT, signal.SIGTERM):
        try:
            signal.signal(sig, lambda *_: eng.request_shutdown())
        except (ValueError, OSError):
            pass  # mis. bukan main thread
    has_key = bool(os.environ.get("ANTHROPIC_API_KEY"))
    print(f"SADAR slice 1 — otak: {'Claude (S2)' if has_key else 'OfflineBackend (stand-in)'}")
    # demo singkat: satu pesan → lingkaran berputar
    if isinstance(eng.perceiver, LocalSensors):
        eng.perceiver.push("ingatkan aku menyiram tanaman besok pagi")
    eng.run(max_ticks=3)
    print("\n[Laporan-diri tertambat]")
    print(eng.introspect_self_report())


if __name__ == "__main__":
    main()
