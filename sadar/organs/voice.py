"""Organ SUARA — indra pendengar (mic→STT) & tangan bersuara (TTS→speaker).

Dipasang di atas inti yang SAMA, nol perubahan di sadar/core/ (tesis buta-platform):
  - MicPerceiver  : implements Perceiver — frasa hasil speech-recognition → Representation persepsi.
  - MacSayEffector: implements Effector — tool 'say' mengucapkan teks lewat speaker (macOS `say`).
  - CompositeEffector: gabung beberapa Effector (mis. catatan + suara) di balik satu port.

KEAMANAN (gratis dari arsitektur):
  - Tool 'say' sudah dijaga HardLimit `_emits_untethered_self_claim`: ucapan ber-klaim-diri
    yang tak tertambat Dosir → DIVETO. SADAR boleh bicara, tapi tak boleh berbohong soal dirinya.
  - STT tak sempurna → MicPerceiver/Recognizer menandai trust<1 (+leaves_premises bila STT awan),
    sehingga Organ C memeriksa masukan suara lebih hati-hati.

Pustaka audio (sounddevice, faster-whisper) di-LAZY-import → modul ini tetap dapat diimpor & diuji
tanpa audio terpasang. TTS via `/usr/bin/say` tak butuh dependensi apa pun.
"""
from __future__ import annotations

import subprocess
import threading
import time

from sadar.core.dosir import Representation
from sadar.core.ports import ActionResult, EffectorSpec, PerceiverSpec, ToolSpec


# ============ TANGAN BERSUARA (TTS via macOS `say`) ============
class MacSayEffector:
    """Effector suara. tool 'say' → ucapkan teks via speaker. Tanpa dependensi (pakai /usr/bin/say)."""

    def __init__(self, voice: str | None = None, rate: int | None = None, timeout: float = 60.0,
                 recognizer=None):
        self.rate = rate            # kata per menit (opsional)
        self.timeout = timeout
        self.note = ""
        self.recognizer = recognizer  # half-duplex: bisukan mic SELAMA bicara → cegah feedback loop.
        self.voice = voice          # mis. "Damayanti" (id_ID) / "Samantha" (en_US); None = bawaan
        if voice and not self._voice_installed(voice):
            self.note = f"suara '{voice}' tak terpasang → pakai suara sistem"
            self.voice = None       # fallback aman: jangan gagal, pakai default sistem

    @staticmethod
    def _voice_installed(name: str) -> bool:
        try:
            out = subprocess.run(["/usr/bin/say", "-v", "?"], capture_output=True,
                                 text=True, timeout=10)
            return any(line.strip().startswith(name) for line in out.stdout.splitlines())
        except Exception:  # noqa: BLE001
            return True     # tak bisa cek → biarkan apa adanya (jangan blokir)

    def list_tools(self) -> list[ToolSpec]:
        return [ToolSpec(name="say", reversible=True, side_effect="external",
                         required_caps=["voice.speak"], usage='args {"text": "..."}')]

    def act(self, tool: str, args: dict) -> ActionResult:
        cb = args.get("_caused_by", [])
        if tool != "say":
            return ActionResult(tool=tool, ok=False, output=f"tool tak dikenal: {tool}", caused_by=cb)
        text = str(args.get("text") or args.get("message") or args.get("content") or "").strip()
        if not text:
            return ActionResult(tool=tool, ok=False, output="teks kosong", caused_by=cb)
        cmd = ["/usr/bin/say"]
        if self.voice:
            cmd += ["-v", self.voice]
        if self.rate:
            cmd += ["-r", str(self.rate)]
        cmd.append(text)
        rec = self.recognizer        # half-duplex: bisukan mic selama /usr/bin/say berbunyi
        if rec is not None and hasattr(rec, "mute"):
            rec.mute()
        try:
            subprocess.run(cmd, check=True, timeout=self.timeout)
            return ActionResult(tool=tool, ok=True, output=f"[diucapkan] {text}", caused_by=cb)
        except Exception as e:  # noqa: BLE001
            return ActionResult(tool=tool, ok=False, output=f"galat say: {e}", caused_by=cb)
        finally:
            if rec is not None and hasattr(rec, "unmute"):
                rec.unmute()

    def spec(self) -> EffectorSpec:
        return EffectorSpec(name="mac-say", provenance="local", trust=1.0)


# ============ GABUNGAN EFFECTOR (catatan + suara di balik satu port) ============
class CompositeEffector:
    """Menggabungkan beberapa Effector. Tool dirutekan ke effector pemiliknya."""

    def __init__(self, *effectors):
        self._effectors = effectors
        self._route: dict[str, object] = {}
        for eff in effectors:
            for t in eff.list_tools():
                self._route[t.name] = eff

    def list_tools(self) -> list[ToolSpec]:
        tools: list[ToolSpec] = []
        for eff in self._effectors:
            tools.extend(eff.list_tools())
        return tools

    def act(self, tool: str, args: dict) -> ActionResult:
        eff = self._route.get(tool)
        if eff is None:
            return ActionResult(tool=tool, ok=False, output=f"tool tak dikenal: {tool}",
                                caused_by=args.get("_caused_by", []))
        return eff.act(tool, args)

    def spec(self) -> EffectorSpec:
        names = "+".join(e.spec().name for e in self._effectors)
        return EffectorSpec(name=f"composite({names})", provenance="local", trust=1.0)


# ============ INDRA PENDENGAR (mic → speech-to-text) ============
class MicPerceiver:
    """Perceiver suara. poll() menguras frasa yang sudah dikenali Recognizer (non-blocking) →
    Representation(source='perception'). Recognizer di-inject (dapat di-mock untuk tes)."""

    def __init__(self, recognizer, emit_clock: bool = True):
        self.recognizer = recognizer
        self.emit_clock = emit_clock

    def poll(self) -> list[Representation]:
        out: list[Representation] = []
        if self.emit_clock:
            import time
            out.append(Representation(content=f"[tik] waktu={time.time():.0f}", source="perception",
                                      trust=1.0, ephemeral=True))
        for phrase in self.recognizer.poll():
            phrase = (phrase or "").strip()
            if phrase:
                out.append(Representation(content=f"pesan pengguna: {phrase}", source="perception",
                                          trust=self.recognizer.trust))
        return out

    def spec(self) -> PerceiverSpec:
        return PerceiverSpec(name=f"mic:{self.recognizer.name}", provenance=self.recognizer.provenance,
                             trust=self.recognizer.trust, leaves_premises=self.recognizer.leaves_premises)


# ============ Recognizer LOKAL (faster-whisper + sounddevice) ============
class WhisperMicRecognizer:
    """STT LOKAL & berdaulat (faster-whisper, di perangkat — tak membocorkan premis).

    Thread latar merekam mic, deteksi suara (energi RMS), lalu transkripsi tiap frasa →
    antrean yang dikuras poll(). Pustaka audio di-import lazy di start().

    CATATAN: jalur audio nyata HANYA dapat diverifikasi di Mac dengan izin Mikrofon aktif.
    """

    name = "faster-whisper(mic)"
    provenance = "local"
    leaves_premises = False
    trust = 0.8     # STT tak sempurna → Organ C lebih hati-hati atas masukan ini

    def __init__(self, model_size: str = "base", language: str = "id", samplerate: int = 16000,
                 window_seconds: float = 3.0, silence_rms: float = 0.006):
        self.model_size = model_size
        self.language = language
        self.samplerate = samplerate
        self.window_seconds = window_seconds
        self.silence_rms = silence_rms          # lewati jendela yang BENAR-benar senyap (hemat CPU)
        self._queue: list[str] = []
        self._lock = threading.Lock()
        self._stop = threading.Event()
        self._thread: threading.Thread | None = None
        self._model = None
        self._mute_until = 0.0      # half-duplex: monotonic time hingga kapan mic diabaikan

    def start(self) -> None:
        try:
            import sounddevice  # noqa: F401
            from faster_whisper import WhisperModel
        except Exception as e:  # noqa: BLE001
            raise RuntimeError(
                "Butuh pustaka audio. Pasang dulu:  pip install sounddevice faster-whisper"
            ) from e
        self._model = WhisperModel(self.model_size, device="cpu", compute_type="int8")
        self._stop.clear()
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()

    def mute(self) -> None:
        """Half-duplex: bisukan mic SELAMA SADAR bicara → cegah feedback loop (speaker→mic→STT).
        Dipanggil KODE sebelum `say`; jendela yang terekam saat ini akan dibuang, bukan ditranskripsi."""
        with self._lock:
            self._mute_until = float("inf")

    def unmute(self, grace: float = 0.4) -> None:
        """Lepas bisu, tapi tetap abaikan mic 'grace' detik lagi agar ekor gema speaker tak tertangkap."""
        with self._lock:
            self._mute_until = time.monotonic() + grace

    def _muted(self) -> bool:
        with self._lock:
            return time.monotonic() < self._mute_until

    def _run(self) -> None:
        # Rekam JENDELA tetap lalu transkripsi (vad_filter Whisper membuang non-ucapan) — sederhana &
        # andal, sejalan dengan mic_test yang sudah terbukti. Tahan terhadap tingkat bising ruangan.
        import numpy as np
        import sounddevice as sd

        win = int(self.samplerate * self.window_seconds)
        while not self._stop.is_set():
            win_start = time.monotonic()
            try:
                audio = sd.rec(win, samplerate=self.samplerate, channels=1, dtype="float32")
                sd.wait()
            except Exception:  # noqa: BLE001
                break
            # half-duplex: buang jendela bila bisu aktif KAPAN PUN selama perekaman ini —
            # mencegah ekor ucapan SADAR (yang sudah terekam sebelum jendela tuntas) lolos.
            with self._lock:
                overlapped = self._mute_until >= win_start
            if overlapped:
                continue                         # SADAR sedang/baru saja bicara → buang
            mono = audio.reshape(-1)
            if float(np.sqrt(np.mean(mono ** 2))) < self.silence_rms:
                continue                         # senyap → tak perlu transkripsi
            try:
                segments, _ = self._model.transcribe(mono, language=self.language, vad_filter=True)
                text = " ".join(s.text for s in segments).strip().strip(".").strip()
            except Exception:  # noqa: BLE001
                text = ""
            if text:
                with self._lock:
                    self._queue.append(text)

    def poll(self) -> list[str]:
        with self._lock:
            out = self._queue[:]
            self._queue.clear()
        return out

    def stop(self) -> None:
        self._stop.set()
        if self._thread is not None:
            self._thread.join(timeout=2.0)
