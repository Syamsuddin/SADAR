"""ProposalStore — USULAN tool baru berbasis markdown. INERT secara konstruksi.

Fase 3: saat pengguna butuh kemampuan yang BELUM ada, SADAR boleh men-DRAFT rancangan tool
(kode effector + izin yang diminta) sebagai dokumen untuk DITINJAU MANUSIA. Dokumen ini:

  - TIDAK PERNAH diimpor, di-`exec`, atau dimuat sebagai kode oleh SADAR (tak ada jalur dynamic-import).
  - TIDAK menambah tool/kapabilitas apa pun ke lingkaran berjalan.
  - Hanya jadi bahan bagi MANUSIA: tinjau → implementasi di organs/ → beri izin di Peran.

Inilah jembatan "skill yang butuh kuasa baru" tanpa melanggar Aturan Kardinal #1: otak mengusulkan,
manusia memutuskan & menulis kode nyata. `.md` = kebenaran (git-friendly, dapat di-review).
"""
from __future__ import annotations

import pathlib
import re
from dataclasses import dataclass, field

_FM_RE = re.compile(r"^---\s*\n(.*?)\n---\s*\n?(.*)$", re.DOTALL)
_LIST_RE = re.compile(r"^\[(.*)\]$")


@dataclass
class Proposal:
    name: str
    description: str = ""
    required_caps: list[str] = field(default_factory=list)
    status: str = "proposed"           # proposed | accepted | rejected (disetel MANUSIA)
    author: str = "conversation"
    body: str = ""                     # rancangan kode + catatan (markdown bebas)


def _val(raw: str):
    raw = raw.strip()
    m = _LIST_RE.match(raw)
    if m:
        inner = m.group(1).strip()
        return [x.strip().strip('"').strip("'") for x in inner.split(",") if x.strip()] if inner else []
    return raw.strip('"').strip("'")


def parse_proposal_md(text: str, fallback_name: str = "") -> Proposal:
    m = _FM_RE.match(text.strip() + "\n")
    fm, body = ("", text.strip())
    if m:
        fm, body = m.group(1), m.group(2).strip()
    data: dict = {}
    for line in fm.splitlines():
        key, sep, val = line.partition(":")
        if sep:
            data[key.strip()] = _val(val)
    caps = data.get("required_caps", [])
    return Proposal(
        name=str(data.get("name", fallback_name) or fallback_name),
        description=str(data.get("description", "")),
        required_caps=caps if isinstance(caps, list) else ([caps] if caps else []),
        status=str(data.get("status", "proposed") or "proposed"),
        author=str(data.get("author", "conversation") or "conversation"),
        body=body,
    )


def proposal_to_md(p: Proposal) -> str:
    fm = [
        f"name: {p.name}",
        f"description: {p.description}",
        f"required_caps: [{', '.join(p.required_caps)}]",
        f"status: {p.status}",
        f"author: {p.author}",
    ]
    return "---\n" + "\n".join(fm) + "\n---\n" + (p.body.strip() + "\n" if p.body.strip() else "")


class ProposalStore:
    def __init__(self, root: str):
        self.root = pathlib.Path(root)

    def _path(self, name: str) -> pathlib.Path:
        safe = re.sub(r"[^a-zA-Z0-9_-]", "-", name.strip().lower())
        return self.root / f"{safe}.md"

    def list(self) -> list[Proposal]:
        if not self.root.exists():
            return []
        out = []
        for p in sorted(self.root.glob("*.md")):
            try:
                out.append(parse_proposal_md(p.read_text(encoding="utf-8"), fallback_name=p.stem))
            except Exception:  # noqa: BLE001
                continue
        return out

    def read(self, name: str) -> Proposal | None:
        p = self._path(name)
        return parse_proposal_md(p.read_text(encoding="utf-8"), fallback_name=name) if p.exists() else None

    def write(self, p: Proposal) -> None:
        self.root.mkdir(parents=True, exist_ok=True)
        self._path(p.name).write_text(proposal_to_md(p), encoding="utf-8")

    def delete(self, name: str) -> bool:
        path = self._path(name)
        if path.exists():
            path.unlink()
            return True
        return False
