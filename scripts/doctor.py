#!/usr/bin/env python3
"""SADAR doctor — audit postur keamanan konfigurasi & izin Peran (read-only).

  python3 scripts/doctor.py                 # audit default (Peran PA)
  python3 scripts/doctor.py --role researcher
  python3 scripts/doctor.py --full-access   # simulasikan cfg.shell.full_access untuk lihat WARN-nya
"""
from __future__ import annotations

import argparse
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
from sadar.config import AppConfig  # noqa: E402
from sadar.doctor import audit_config, format_report  # noqa: E402
from sadar.roles.registry import get_role  # noqa: E402


def main() -> int:
    ap = argparse.ArgumentParser(description="Audit konfigurasi SADAR (inert/read-only).")
    ap.add_argument("--role", default="pa")
    ap.add_argument("--full-access", action="store_true")
    args = ap.parse_args()
    cfg = AppConfig(shell={"full_access": args.full_access})
    role = get_role(args.role)
    print(f"SADAR doctor — Peran: {role.identity}\n")
    print(format_report(audit_config(cfg, role)))
    return 0


if __name__ == "__main__":
    sys.exit(main())
