"""Config Doctor (Slice 4.3) — audit konfigurasi & izin BERISIKO. Read-only, deterministik (KODE).

Tak mengubah apa pun; hanya melaporkan temuan agar manusia sadar postur keamanannya. Dipakai
lewat `scripts/doctor.py`. Tingkat: WARN (perlu perhatian) / INFO (sekadar kesadaran).
"""
from __future__ import annotations

_RISKY_CAPS = {"shell.write", "tool.manage", "skill.write", "tool.draft", "notes.delete"}


def audit_config(cfg, role) -> list[tuple[str, str]]:
    """Kembalikan daftar (tingkat, pesan). Kosong = tak ada yang menonjol."""
    out: list[tuple[str, str]] = []

    if getattr(cfg.shell, "full_access", False):
        out.append(("WARN", "CLI AKSES-PENUH aktif (denylist, tanpa lantai-mutlak): perintah destruktif "
                            "yang tak terdaftar bisa jalan LANGSUNG. Pakai hanya di mesin tepercaya; "
                            "pertimbangkan sandbox (cfg.shell.sandbox)."))
    if getattr(cfg.web, "allow_private", False):
        out.append(("WARN", "web_fetch mengizinkan host privat/loopback → risiko SSRF. Set web.allow_private=False."))
    if getattr(cfg.store, "allow_remote", False):
        out.append(("WARN", "store remote diizinkan → premis bisa keluar mesin (langgar local-first)."))

    risky = _RISKY_CAPS & set(getattr(role, "granted_caps", set()))
    if risky:
        out.append(("INFO", f"Peran '{role.identity}' memegang kapabilitas berdampak: "
                            f"{', '.join(sorted(risky))} — pastikan memang diinginkan."))
    import importlib.util
    emb = getattr(cfg.store, "embedder", "")
    st_ok = importlib.util.find_spec("sentence_transformers") is not None
    if emb in ("hashing", "local-hash") or (emb == "auto" and not st_ok):
        out.append(("INFO", "Embedder LEKSIKAL (hashing) aktif: metrik semantik (coherence/integration/"
                            "surprise) & grounding klaim-dunia berbasis tumpang-tindih kata, bukan makna. "
                            "Pasang `sentence-transformers` → embedder 'auto' otomatis jadi semantik."))
    if getattr(cfg.brain, "backend", "auto") in ("auto", "claude"):
        out.append(("INFO", "Otak dapat memakai Claude (remote): premis keluar → Organ C menaikkan caution. "
                            "Untuk berdaulat penuh, set brain.backend='ollama' atau 'offline'."))
    return out


def format_report(findings: list[tuple[str, str]]) -> str:
    if not findings:
        return "✓ Tak ada temuan menonjol. Konfigurasi tampak waras."
    icon = {"WARN": "⚠️ ", "INFO": "•  "}
    lines = [f"{icon.get(lvl, '')}[{lvl}] {msg}" for lvl, msg in findings]
    warn = sum(1 for lvl, _ in findings if lvl == "WARN")
    return "\n".join(lines) + f"\n\n{warn} WARN, {len(findings) - warn} INFO."
