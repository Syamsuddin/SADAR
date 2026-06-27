"""Voice chat dengan SADAR — pendengaran (mic→STT) sebagai indra, suara (speaker) sebagai keluaran.

Jalankan:  python3 -m sadar.voice_chat
Prasyarat (sekali):  pip install sounddevice faster-whisper
                     + izinkan Mikrofon untuk Terminal di System Settings → Privacy & Security → Microphone.

Alur: mikrofon → speech-to-text → persepsi SADAR → lingkaran kognitif → SADAR menjawab dengan
TINDAKAN (mis. mencatat) lalu MENGUCAPKANNYA lewat speaker. Setiap ucapan tetap melewati gerbang
konstitusi (anti-fabrikasi), jadi SADAR boleh bicara tapi tak boleh berbohong soal dirinya.

Catatan jujur: untuk jawaban PERCAKAPAN yang disusun SADAR sendiri, pakai otak Claude
(set ANTHROPIC_API_KEY). Tanpa kunci, otak stand-in hanya mencatat & mengonfirmasi via suara.

CLI (cli=True): SADAR dapat menjalankan perintah terminal lewat tool yang sudah ada —
'shell' (baca-saja, allowlist, langsung) & 'shell_write' (mutasi, WAJIB konfirmasi suara HITL).
Semua tetap digerbang KODE: kapabilitas, allowlist, tolak metakarakter, timeout. Perintah
destruktif (rm/dd/sudo) sengaja TAK di allowlist. Konfirmasi mutasi: ucapkan 'konfirmasi'/'batal'.
"""
from __future__ import annotations

import re
import time

from sadar.config import AppConfig
from sadar.core.constitution import ProposedAction
from sadar.main import build_sadar
from sadar.organs.confirm import confirm_summary

_STOP_WORDS = ("berhenti", "matikan", "stop", "sampai jumpa", "keluar")
# Konfirmasi/penolakan SUARA untuk aksi mutasi (shell_write) yang ditahan gerbang HITL.
# Hanya berlaku saat ada aksi tertunda → kata umum ("lakukan") tak memicu apa-apa tanpa pending.
_CONFIRM_WORDS = ("konfirmasi", "ya lakukan", "ya jalankan", "iya lakukan", "iya jalankan",
                  "setuju", "lanjutkan", "lakukan sekarang", "kerjakan sekarang")
_CANCEL_WORDS = ("batal", "batalkan", "tidak jadi", "jangan jadi", "jangan dijalankan")
_HITL_RE = re.compile(r"\[KONFIRMASI DIBUTUHKAN id=([0-9a-f]+)\]")


def _speak(eng, text: str) -> None:
    """Ucapkan via tool 'say' — TETAP lewat gerbang konstitusi (ucapan bohong-diri diveto).
    Half-duplex (bisukan mic saat bicara) kini ditangani MacSayEffector → mencakup SEMUA ucapan."""
    text = (text or "").strip()
    if not text:
        return
    action = ProposedAction(tool="say", args={"text": text}, reversible=True,
                            required_caps=["voice.speak"])
    if eng.constitution.gate.vet(action, eng.d).allowed:
        eng.effector.act("say", {"text": text})


def main() -> None:
    # voice=True → mic+speaker; cli=True + full_access → satu tool 'shell' menerima perintah APA PUN;
    # KODE (denylist) menyaring: perintah berisiko WAJIB konfirmasi suara, aman → langsung.
    eng = build_sadar(AppConfig(loop={"tick_interval_s": 0.0}, shell={"full_access": True}),
                      voice=True, cli=True)
    rec = eng.perceiver.recognizer
    brain = type(eng.backend).__name__
    has_cli = "shell" in getattr(eng, "_tools", {})
    print(f"SADAR voice — otak: {brain}{' | CLI: AKSES-PENUH' if has_cli else ''}", end="")
    if brain != "ClaudeBackend":
        print("  ⚠️  STAND-IN (tanpa API key) → hanya mencatat, TAK menjawab. "
              "Set ANTHROPIC_API_KEY untuk otak Claude.", end="")
    print("\nMendengarkan… (Ctrl-C untuk berhenti, atau ucapkan 'berhenti').")
    print("Pastikan izin Mikrofon untuk Terminal aktif.")
    if has_cli:
        print("⚠️  CLI AKSES-PENUH: perintah aman (ls/cat/pwd/grep/…) jalan langsung; "
              "perintah BERISIKO (rm/sudo/mv/pipe/redirect/dll.) diringkas lalu minta 'setuju'/'batal'. "
              "TANPA lantai-mutlak — apa pun bisa dijalankan setelah disetujui.")
    try:
        rec.start()
    except RuntimeError as e:
        print(f"\n[GAGAL] {e}")
        return
    _speak(eng, "Aku mendengarkan.")
    spoken: set[str] = set()
    pending_rid: str | None = None        # aksi mutasi CLI menunggu konfirmasi suara (HITL)
    try:
        while not eng.d.shutdown_requested:
            eng.tick()
            for r in list(eng.d.workspace.items):
                if r.id in spoken:
                    continue
                spoken.add(r.id)
                if r.source == "perception" and r.content.startswith("pesan pengguna:"):
                    heard = r.content.split(":", 1)[1].strip()
                    print("Kamu :", heard)
                    low = heard.lower()
                    if any(w in low for w in _STOP_WORDS):
                        eng.request_shutdown()            # kata-henti = sinyal KONTROL (deterministik)
                    elif pending_rid and any(w in low for w in _CANCEL_WORDS):
                        eng.cancel(pending_rid)           # tolak aksi mutasi (KODE)
                        pending_rid = None
                    elif pending_rid and any(w in low for w in _CONFIRM_WORDS):
                        eng.confirm(pending_rid)          # setujui aksi mutasi (KODE, bukan LLM)
                        pending_rid = None
                elif r.source == "action_result" and not r.content.startswith("[diucapkan]"):
                    # Hasil alat (catatan/shell) → TAMPIL di layar; SUARA disampaikan otak lewat 'reply'
                    # (mencegah membaca output mentah spt daftar `ls` keras-keras).
                    print("SADAR (alat):", r.content)
                elif r.source == "thought" and r.content.startswith("[KONFIRMASI DIBUTUHKAN"):
                    print("SADAR:", r.content)            # perintah MENTAH tetap tampil di layar (verifikasi)
                    m = _HITL_RE.search(r.content)
                    if m:
                        pending_rid = m.group(1)
                    ringkas = confirm_summary(r.content)
                    # Ucapkan RINGKASAN (bukan perintah mentah panjang) + konfirmasi yang jelas.
                    _speak(eng, f"Perlu izin untuk {ringkas}. Apakah Pak Syams setuju? "
                                "Ucapkan 'setuju' atau 'batal'.")
                elif r.source == "thought" and r.content.startswith("[DIBATALKAN"):
                    print("SADAR:", r.content)
                    _speak(eng, "Baik, kubatalkan.")
                elif r.source == "thought" and r.content.startswith("[DEGRADED"):
                    print("SADAR:", r.content)            # otak-dalam tak terjangkau → jujur, jangan bisu
                    _speak(eng, "Maaf, otak-dalamku sedang tak terjangkau. "
                                "Aku hanya bisa menanggapi seadanya.")
                elif r.source == "thought" and r.content.startswith("[VETO"):
                    print("SADAR:", r.content)            # jawaban ditahan konstitusi → ucapkan, jangan bisu
                    _speak(eng, "Maaf, ada yang aku tahan karena belum dapat "
                                "kupertanggungjawabkan dengan jujur.")
            time.sleep(0.15)
    except KeyboardInterrupt:
        eng.request_shutdown()
    finally:
        _speak(eng, "Sampai jumpa.")
        rec.stop()


if __name__ == "__main__":
    main()
