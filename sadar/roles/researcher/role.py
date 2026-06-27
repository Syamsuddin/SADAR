"""Peran Researcher (read-only) — BUKTI tesis buta-platform & permission model.

Dipasang di atas inti yang SAMA, nol perubahan di sadar/core/. Hanya diberi kapabilitas
BACA → gerbang konstitusi otomatis memveto setiap aksi tulis/hapus (capability_not_granted),
tanpa cabang-peran di inti. Skill-set & maksud berbeda; mekanisme keselamatan identik.
"""
from __future__ import annotations

from sadar.core.dosir import Purpose
from sadar.roles.registry import Role

RESEARCHER_ROLE = Role(
    identity="Peneliti read-only",
    purpose=Purpose(statement=(
        "Menemukan dan menyajikan kembali informasi yang tersimpan dengan jujur — TANPA "
        "mengubah apa pun, dan jujur tentang apa yang tak kuketahui."
    )),
    value_emphasis=["honesty"],
    skills=["recall"],
    granted_caps={"notes.read"},   # hanya baca/recall; tulis & hapus akan diveto konstitusi
)
