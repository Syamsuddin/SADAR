"""Buta-platform — klaim arsitektural dibuat DAPAT DIFALSIFIKASI oleh uji.

Inti (sadar/core/) tak boleh tahu apa pun tentang Peran konkret (PA) maupun
implementasi organ konkret. Jika bocor, uji ini GUGUR — properti ditegakkan,
bukan sekadar diasersikan di dokumen.
"""
from __future__ import annotations

import pathlib
import re

CORE = pathlib.Path(__file__).resolve().parents[1] / "sadar" / "core"


def _core_files():
    files = sorted(CORE.glob("*.py"))
    assert files, "direktori core/ tak ditemukan / kosong"
    return files


# --- inti tak mereferensikan Peran konkret -------------------------------------
def test_core_has_no_role_refs():
    banned = ["personal assistant", "pa_role", "roles.pa", "sadar.roles", "import roles"]
    for f in _core_files():
        text = f.read_text(encoding="utf-8").lower()
        for token in banned:
            assert token not in text, f"core/{f.name} bocor referensi peran: {token!r}"


# --- inti tak BERCABANG pada peran (bau #1: `if role == "PA":`) -----------------
def test_core_has_no_role_branching():
    leak = re.compile(r'\brole\b\s*==|==\s*["\'](pa|personal)', re.IGNORECASE)
    for f in _core_files():
        for n, line in enumerate(f.read_text(encoding="utf-8").splitlines(), 1):
            assert not leak.search(line), f"core/{f.name}:{n} bercabang pada peran (langgar buta-platform)"


# --- inti tak mengimpor organ konkret (ports-and-adapters) ---------------------
def test_core_does_not_import_organs():
    for f in _core_files():
        text = f.read_text(encoding="utf-8")
        assert "sadar.organs" not in text, f"core/{f.name} mengimpor organ konkret (langgar heksagonal)"


# --- inti tak mengimpor SDK eksternal (otak hanya lewat port) ------------------
def test_core_is_substrate_agnostic():
    for f in _core_files():
        text = f.read_text(encoding="utf-8")
        assert "import anthropic" not in text, f"core/{f.name} terikat vendor otak tertentu"
        assert "sentence_transformers" not in text, f"core/{f.name} terikat embedder tertentu"
