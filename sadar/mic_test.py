"""Tes mikrofon → speech-to-text untuk SADAR. INTERAKTIF: tekan ENTER, bicara, lihat hasilnya.

Jalankan:  .venv/bin/python -m sadar.mic_test
Prasyarat: izin Mikrofon untuk Terminal aktif (System Settings → Privacy & Security → Microphone).
Ketik 'q' lalu ENTER untuk keluar.
"""
from __future__ import annotations


def main() -> None:
    try:
        import numpy as np
        import sounddevice as sd
        from faster_whisper import WhisperModel
    except Exception as e:  # noqa: BLE001
        print("Butuh pustaka audio:  pip install sounddevice faster-whisper —", e)
        return

    sr, secs = 16000, 5
    try:
        ins = [d["name"] for d in sd.query_devices() if d["max_input_channels"] > 0]
    except Exception as e:  # noqa: BLE001
        print("Tak bisa membaca perangkat audio:", e)
        return
    print("Mikrofon terdeteksi:", ins or "TIDAK ADA")
    print("Memuat model Whisper (base)…")
    model = WhisperModel("base", device="cpu", compute_type="int8")
    print(f"Siap. Tekan ENTER lalu bicara ~{secs} detik. (ketik 'q' + ENTER untuk keluar)")

    while True:
        if input("> ").strip().lower() == "q":
            break
        print(f"  merekam {secs} detik… BICARA SEKARANG.")
        audio = sd.rec(int(secs * sr), samplerate=sr, channels=1, dtype="float32")
        sd.wait()
        mono = audio.reshape(-1)
        rms = float(np.sqrt(np.mean(mono ** 2)))
        segments, _ = model.transcribe(mono, language="id")
        text = " ".join(s.text for s in segments).strip()
        if text:
            print(f"  [RMS {rms:.4f}] kamu bilang: {text!r}")
        else:
            print(f"  [RMS {rms:.4f}] (tak ada ucapan terdeteksi — cek volume/izin mic)")


if __name__ == "__main__":
    main()
