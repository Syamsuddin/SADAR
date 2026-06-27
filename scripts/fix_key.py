#!/usr/bin/env python3
"""Perbaiki baris `export ANTHROPIC_API_KEY=...` di ~/.zshrc (atau berkas rc lain).

MASALAH yang diatasi: editor/copy-paste sering menyisipkan KUTIP KERITING (’ ‘ “ ”,
U+2018/2019/201C/201D) alih-alih kutip lurus ('). Shell tak mengenalinya sebagai kutip,
jadi karakter itu IKUT jadi bagian nilai key → key rusak → Anthropic API balas 401 →
SADAR jatuh ke mode DEGRADED (otak-dalam tak terjangkau) padahal key-nya sebetulnya valid.
Skrip ini juga membuang baris export DUPLIKAT, menyisakan SATU baris bersih tanpa kutip.

DISIPLIN: nilai key TIDAK PERNAH dicetak (hanya 6 char terakhir untuk identifikasi).
Selalu membuat backup `<file>.bak-sadar` sebelum menulis.

Pakai:
    python3 scripts/fix_key.py                 # perbaiki ~/.zshrc
    python3 scripts/fix_key.py --check         # hanya laporkan (dry-run, tak menulis)
    python3 scripts/fix_key.py --file ~/.bashrc --var OPENAI_API_KEY
    python3 scripts/fix_key.py --verify        # uji validitas key ke Anthropic (butuh paket anthropic)

Setelah perbaikan:  source ~/.zshrc  &&  echo "${ANTHROPIC_API_KEY:0:7}"   # harus 'sk-ant-'
"""
from __future__ import annotations

import argparse
import os
import pathlib
import re
import shutil
import sys

# Semua varian kutip yang mungkin mengapit nilai (lurus + keriting/typografis).
_QUOTES = ("'", '"', "‘", "’", "“", "”")


def _strip_quotes(value: str) -> str:
    v = value.strip()
    # buang kutip pengapit berulang dari kedua tepi (mis. ’sk-...' → sk-...)
    changed = True
    while changed:
        changed = False
        for q in _QUOTES:
            if v[:1] == q:
                v = v[1:]
                changed = True
            if v[-1:] == q:
                v = v[:-1]
                changed = True
    return v.strip()


def fix(path: pathlib.Path, var: str, check: bool) -> tuple[bool, str | None]:
    """Kembalikan (berubah, key). 'key' = nilai bersih bila ketemu (untuk --verify)."""
    lines = path.read_text().splitlines()
    pat = re.compile(rf"^\s*export\s+{re.escape(var)}=(.+)$")

    key: str | None = None
    first_idx: int | None = None
    raw_lines: list[str] = []   # baris export mentah yang terpengaruh (untuk laporan)
    out: list[str] = []
    for ln in lines:
        m = pat.match(ln)
        if m and not ln.lstrip().startswith("#"):
            raw_lines.append(ln)
            cleaned = _strip_quotes(m.group(1))
            if cleaned and not cleaned.isspace():
                key = cleaned                  # baris terakhir menang (umumnya yang dimaksud aktif)
            if first_idx is None:
                first_idx = len(out)
                out.append("__PLACEHOLDER__")  # tandai posisi baris bersih tunggal
            continue                           # semua duplikat dilewati
        out.append(ln)

    if first_idx is None or key is None:
        return False, None

    clean_line = f"export {var}={key}"          # tanpa kutip — key tak mengandung spasi
    out[first_idx] = clean_line

    # tentukan apakah ada perubahan nyata (kutip rusak / duplikat)
    already_ok = len(raw_lines) == 1 and raw_lines[0].strip() == clean_line
    if already_ok:
        return False, key

    if not check:
        shutil.copy2(path, str(path) + ".bak-sadar")
        path.write_text("\n".join(out) + "\n")
    return True, key


def main() -> int:
    ap = argparse.ArgumentParser(description="Luruskan kutip & dedupe baris export API key di rc shell.")
    ap.add_argument("--file", default="~/.zshrc", help="berkas rc target (default: ~/.zshrc)")
    ap.add_argument("--var", default="ANTHROPIC_API_KEY", help="nama env var (default: ANTHROPIC_API_KEY)")
    ap.add_argument("--check", action="store_true", help="dry-run: laporkan saja, jangan menulis")
    ap.add_argument("--verify", action="store_true", help="uji validitas key ke Anthropic (butuh paket anthropic)")
    args = ap.parse_args()

    path = pathlib.Path(os.path.expanduser(args.file))
    if not path.exists():
        print(f"GAGAL: berkas tak ada: {path}")
        return 1

    changed, key = fix(path, args.var, args.check)
    if key is None:
        print(f"Tak menemukan baris `export {args.var}=...` (non-komentar) di {path}.")
        return 1

    tail = f"...{key[-6:]}"
    if args.check:
        status = "PERLU PERBAIKAN (kutip rusak / duplikat)" if changed else "sudah bersih"
        print(f"[dry-run] {args.var} {tail}: {status}")
    elif changed:
        print(f"OK ✓ {path} → 1 baris bersih tanpa kutip ({args.var} {tail}). Backup: {path}.bak-sadar")
        print(f"   Jalankan:  source {args.file}  &&  echo \"${{{args.var}:0:7}}\"   # harus 'sk-ant-'")
    else:
        print(f"{args.var} {tail}: sudah bersih, tak ada yang diperbaiki.")

    if args.verify:
        try:
            import anthropic
        except ImportError:
            print("(--verify dilewati: paket 'anthropic' belum terpasang)")
            return 0
        try:
            c = anthropic.Anthropic(api_key=key)
            c.messages.create(model="claude-sonnet-4-6", max_tokens=5,
                              messages=[{"role": "user", "content": "hi"}])
            print(f"VERIFY: key {tail} VALID ✔ (Anthropic menerima)")
        except anthropic.AuthenticationError:
            print(f"VERIFY: key {tail} INVALID (401) — rotasi/ganti key.")
        except Exception as e:  # noqa: BLE001
            print(f"VERIFY: tak bisa memastikan ({type(e).__name__}: {str(e)[:60]})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
