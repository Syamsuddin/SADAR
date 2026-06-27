"""Chat TEKS dengan SADAR — ketik pesan, SADAR menjawab lewat lingkaran kognitif yang SAMA.

Jalankan:  python3 -m sadar.text_chat

Bedanya dengan voice_chat hanya KANAL I/O (keyboard, bukan mic/speaker). Otak, Dosir, konstitusi,
Organ C, jalur 'reply', dan CLI identik. Otak = Claude bila ANTHROPIC_API_KEY ada; selainnya
OfflineBackend (stand-in: hanya mencatat). CLI akses-penuh aktif: perintah aman jalan langsung,
perintah berisiko diringkas lalu minta konfirmasi (ketik 'setuju'/'batal').

Perintah REPL:  /keluar (atau Ctrl-D) untuk berhenti.
"""
from __future__ import annotations

import re

from sadar.config import AppConfig
from sadar.main import build_sadar
from sadar.organs.confirm import confirm_summary

_STOP = {"/keluar", "/exit", "/quit", "/stop", "keluar"}
_CONFIRM = {"setuju", "ya", "konfirmasi", "lanjutkan", "lakukan", "ok", "oke", "y"}
_CANCEL = {"batal", "batalkan", "tidak", "jangan", "n"}
_HITL_RE = re.compile(r"\[KONFIRMASI DIBUTUHKAN id=([0-9a-f]+)\]")


def drain(eng, seen: set, pending: str | None) -> str | None:
    """Cetak item BARU di workspace sebagai giliran SADAR; kembalikan id konfirmasi tertunda terbaru.
    Perintah MENTAH tetap tampil (mode teks aman dibaca); konfirmasi diringkas."""
    for r in list(eng.d.workspace.items):
        if r.id in seen:
            continue
        seen.add(r.id)
        c = r.content
        if r.source == "thought" and c.startswith("[reply] "):
            print("SADAR:", c[len("[reply] "):].strip())
        elif r.source == "thought" and c.startswith("[KONFIRMASI DIBUTUHKAN"):
            print("SADAR:", c)                         # baris mentah utuh (audit di layar)
            m = _HITL_RE.search(c)
            if m:
                pending = m.group(1)
            print(f"SADAR: Perlu izin untuk {confirm_summary(c)}. Apakah Pak Syams setuju? "
                  "Ketik 'setuju' atau 'batal'.")
        elif r.source == "thought" and c.startswith("[DIBATALKAN"):
            print("SADAR: Baik, kubatalkan.")
        elif r.source == "thought" and c.startswith("[DEGRADED"):
            print("SADAR: (otak-dalam tak terjangkau — aku hanya bisa refleks ringan)")
        elif r.source == "thought" and c.startswith("[VETO"):
            print("SADAR: (ada yang kutahan karena belum dapat kupertanggungjawabkan dengan jujur)")
        elif r.source == "action_result" and not c.startswith("[diucapkan]"):
            print("SADAR:", c)                         # sapaan refleks / keluaran alat (catatan/shell)
    return pending


def main() -> None:
    # cli=True + full_access → satu tool 'shell' menerima perintah apa pun; KODE menyaring risiko.
    eng = build_sadar(AppConfig(loop={"tick_interval_s": 0.0}, shell={"full_access": True}), cli=True)
    brain = type(eng.backend).__name__
    has_cli = "shell" in getattr(eng, "_tools", {})
    print(f"SADAR teks — otak: {brain}{' | CLI: AKSES-PENUH' if has_cli else ''}")
    if brain != "ClaudeBackend":
        print("⚠️  STAND-IN (tanpa API key) → hanya mencatat, TAK menjawab. "
              "Set ANTHROPIC_API_KEY untuk otak Claude.")
    if has_cli:
        print("⚠️  CLI AKSES-PENUH: perintah aman jalan langsung; berisiko diringkas + minta 'setuju'/'batal'.")
    print("Ketik pesan (panggil 'Yanti, …' untuk sapaan). /keluar untuk berhenti.")

    seen: set = set()
    pending: str | None = None
    for r in eng.d.workspace.items:                    # serap kondisi awal tanpa cetak
        seen.add(r.id)
    try:
        while not eng.d.shutdown_requested:
            try:
                line = input("\nKamu: ").strip()
            except EOFError:
                break
            if not line:
                continue
            low = line.lower()
            if low in _STOP:
                break
            if pending and low in _CANCEL:
                eng.cancel(pending)
                pending = None
            elif pending and low in _CONFIRM:
                eng.confirm(pending)                   # persetujuan manusia (KODE, bukan LLM)
                pending = None
            else:
                eng.perceiver.push(line)
                eng.tick()                             # satu tik: deliberasi agentic (plan_budget) tuntas
            pending = drain(eng, seen, pending)
    except KeyboardInterrupt:
        pass
    finally:
        print("\nSADAR: Sampai jumpa.")


if __name__ == "__main__":
    main()
