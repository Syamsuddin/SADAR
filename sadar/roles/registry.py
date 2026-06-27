"""Registry Peran — INSTANS dipasang di atas inti bebas-peran.

Peran adalah DATA yang disuntikkan (purpose + kapabilitas + skills), bukan cabang di inti.
Membuktikan tesis buta-platform: menambah Peran (mis. researcher read-only) = nol perubahan
di sadar/core/ (dijaga test_blind_platform). Kapabilitas yang diberikan → permission model (C1).
"""
from __future__ import annotations

from pydantic import BaseModel, Field

from sadar.core.dosir import Purpose


class Role(BaseModel):
    identity: str
    purpose: Purpose
    value_emphasis: list[str] = Field(default_factory=list)
    skills: list[str] = Field(default_factory=list)
    granted_caps: set[str] = Field(default_factory=set)   # izin yang diberikan ke gerbang konstitusi
    wake_words: list[str] = Field(default_factory=list)   # nama-panggilan pemicu refleks sapaan
    greeting: str = ""                                    # sapaan tetap saat dipanggil namanya
    persona: str = ""                                     # nada/suara bicara (gaya, BUKAN klaim-diri)


def get_role(name: str) -> Role:
    """Resolusi Peran terdaftar (lazy-import agar tak ada siklus registry<->role)."""
    from sadar.roles.pa.role import PA_ROLE
    from sadar.roles.researcher.role import RESEARCHER_ROLE

    roles = {"pa": PA_ROLE, "researcher": RESEARCHER_ROLE}
    if name not in roles:
        raise ValueError(f"peran tak dikenal: {name!r} (tersedia: {sorted(roles)})")
    return roles[name]
