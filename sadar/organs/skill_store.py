"""SkillStore — kompetensi berbasis MARKDOWN. `.md` = kebenaran; objek Skill = turunan.

Pola identik MarkdownVectorStore: berkas adalah sumber kebenaran, dapat di-`reload` kapan saja,
git-friendly, dan dapat diedit manusia maupun ditulis lewat tool (Fase 2 — skill creator).

CAPABILITY FIREWALL (Aturan Kardinal #1): sebuah skill hanya AKTIF bila SEMUA `required_caps`-nya
diberikan Peran DAN semua `tools`-nya benar-benar tersedia. Skill yang menuntut kapabilitas/tool
tak-dimiliki → INACTIVE (tak diam-diam berfungsi) — anti-fabrikasi diterapkan ke kompetensi.

Skill DARI PERCAKAPAN tak pernah menambah kuasa: ia hanya mengkomposisi tool yang sudah diizinkan.
Menumbuhkan tool mentah baru tetap butuh manusia (kode di organs/ + grant di Peran).
"""
from __future__ import annotations

import pathlib
import re
from dataclasses import dataclass, field


@dataclass
class Skill:
    name: str
    description: str = ""
    know_how: str = ""                 # body markdown — prosa kompetensi/langkah
    when: str = ""                     # isyarat kapan relevan
    tools: list[str] = field(default_factory=list)
    required_caps: list[str] = field(default_factory=list)
    status: str = "active"             # active | inactive (disetel manusia/tool)
    author: str = "builtin"           # builtin | conversation — jejak asal

    def is_active(self, granted_caps: set[str], available_tools: set[str] | None = None) -> bool:
        """FIREWALL: aktif hanya bila status active, caps ⊆ granted, dan tools ⊆ tersedia."""
        if self.status != "active":
            return False
        if not set(self.required_caps).issubset(set(granted_caps)):
            return False
        if available_tools is not None and not set(self.tools).issubset(set(available_tools)):
            return False
        return True


_FM_RE = re.compile(r"^---\s*\n(.*?)\n---\s*\n?(.*)$", re.DOTALL)
_LIST_RE = re.compile(r"^\[(.*)\]$")


def _parse_value(raw: str):
    raw = raw.strip()
    m = _LIST_RE.match(raw)
    if m:
        inner = m.group(1).strip()
        return [x.strip().strip('"').strip("'") for x in inner.split(",") if x.strip()] if inner else []
    return raw.strip('"').strip("'")


def parse_skill_md(text: str, fallback_name: str = "") -> Skill:
    """Parse markdown (frontmatter + body) → Skill. Tahan-banting: field absen → default."""
    m = _FM_RE.match(text.strip() + "\n")
    fm, body = ("", text.strip())
    if m:
        fm, body = m.group(1), m.group(2).strip()
    data: dict = {}
    for line in fm.splitlines():
        if not line.strip() or line.lstrip().startswith("#"):
            continue
        key, sep, val = line.partition(":")
        if not sep:
            continue
        data[key.strip()] = _parse_value(val)
    def s(k, d=""):
        v = data.get(k, d)
        return v if isinstance(v, str) else d
    def lst(k):
        v = data.get(k, [])
        return v if isinstance(v, list) else ([v] if v else [])
    return Skill(
        name=s("name", fallback_name),
        description=s("description"),
        know_how=body,
        when=s("when"),
        tools=lst("tools"),
        required_caps=lst("required_caps"),
        status=s("status", "active") or "active",
        author=s("author", "builtin") or "builtin",
    )


def skill_to_md(sk: Skill) -> str:
    """Serialisasi Skill → markdown (frontmatter + body)."""
    def fmt_list(xs):
        return "[" + ", ".join(xs) + "]"
    fm = [
        f"name: {sk.name}",
        f"description: {sk.description}",
        f"tools: {fmt_list(sk.tools)}",
        f"when: {sk.when}",
        f"required_caps: {fmt_list(sk.required_caps)}",
        f"status: {sk.status}",
        f"author: {sk.author}",
    ]
    return "---\n" + "\n".join(fm) + "\n---\n" + (sk.know_how.strip() + "\n" if sk.know_how.strip() else "")


class SkillStore:
    """Pengelola skill markdown. Sumber kebenaran = berkas `.md` di `root`."""

    def __init__(self, root: str):
        self.root = pathlib.Path(root)

    def _path(self, name: str) -> pathlib.Path:
        safe = re.sub(r"[^a-zA-Z0-9_-]", "-", name.strip().lower())
        return self.root / f"{safe}.md"

    def list(self) -> list[Skill]:
        if not self.root.exists():
            return []
        out: list[Skill] = []
        for p in sorted(self.root.glob("*.md")):
            try:
                out.append(parse_skill_md(p.read_text(encoding="utf-8"), fallback_name=p.stem))
            except Exception:  # noqa: BLE001 — berkas rusak tak boleh menjatuhkan loader
                continue
        return out

    def read(self, name: str) -> Skill | None:
        p = self._path(name)
        if not p.exists():
            return None
        return parse_skill_md(p.read_text(encoding="utf-8"), fallback_name=name)

    def write(self, sk: Skill) -> None:
        self.root.mkdir(parents=True, exist_ok=True)
        self._path(sk.name).write_text(skill_to_md(sk), encoding="utf-8")

    def delete(self, name: str) -> bool:
        p = self._path(name)
        if p.exists():
            p.unlink()
            return True
        return False

    def active_for(self, granted_caps: set[str], available_tools: set[str] | None = None,
                   names: list[str] | None = None) -> list[Skill]:
        """Skill yang LOLOS firewall (caps+tools) untuk Peran ini. `names` (opsional) membatasi
        ke himpunan skill yang dipilih Peran; None = semua yang lolos."""
        sel = set(names) if names else None
        return [sk for sk in self.list()
                if (sel is None or sk.name in sel) and sk.is_active(granted_caps, available_tools)]
