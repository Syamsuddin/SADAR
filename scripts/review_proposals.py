#!/usr/bin/env python3
"""Tinjau usulan tool yang dibuat SADAR (Fase 3). Untuk MANUSIA.

Usulan bersifat INERT (tak pernah dijalankan SADAR). Alur peninjauan:
  1. lihat daftar         : python3 scripts/review_proposals.py
  2. baca satu usulan     : python3 scripts/review_proposals.py --show <nama>
  3. bila layak           : implementasi effector di sadar/organs/, beri izin di Peran,
                            lalu tandai diterima: --accept <nama>  (atau --reject <nama>)

Tidak ada kode usulan yang dieksekusi oleh skrip ini — hanya membaca/menulis status di berkas .md.
"""
from __future__ import annotations

import argparse
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
from sadar.organs.proposal_store import ProposalStore  # noqa: E402


def main() -> int:
    ap = argparse.ArgumentParser(description="Tinjau usulan tool SADAR (inert).")
    ap.add_argument("--root", default=str(pathlib.Path(__file__).resolve().parents[1] / "sadar" / "proposals"))
    ap.add_argument("--show", metavar="NAMA")
    ap.add_argument("--accept", metavar="NAMA")
    ap.add_argument("--reject", metavar="NAMA")
    args = ap.parse_args()
    store = ProposalStore(args.root)

    if args.show:
        p = store.read(args.show)
        if not p:
            print(f"usulan '{args.show}' tak ditemukan"); return 1
        print(f"# {p.name}  [{p.status}]  (oleh {p.author})")
        print(f"izin diminta: {', '.join(p.required_caps) or '—'}\n")
        print(p.body)
        return 0

    for flag, status in (("accept", "accepted"), ("reject", "rejected")):
        name = getattr(args, flag)
        if name:
            p = store.read(name)
            if not p:
                print(f"usulan '{name}' tak ditemukan"); return 1
            p.status = status
            store.write(p)
            print(f"usulan '{name}' → status: {status}")
            return 0

    items = store.list()
    if not items:
        print("(belum ada usulan tool)")
        return 0
    print(f"Usulan tool di {args.root}:")
    for p in items:
        print(f"  - {p.name:24} [{p.status:8}] izin: {', '.join(p.required_caps) or '—'}  — {p.description[:60]}")
    print("\nLihat detail: --show <nama> | tandai: --accept/--reject <nama>")
    return 0


if __name__ == "__main__":
    sys.exit(main())
