"""ToolDraftEffector — Fase 3: otak MENGUSULKAN tool baru (kode + izin) untuk ditinjau MANUSIA.

Tool:
  - tool_propose   : tulis DRAFT tool baru → disimpan sebagai dokumen (INERT). cap: tool.draft.
  - tool_proposals : daftar usulan + status (baca). cap: tool.draft.

KESELAMATAN (Aturan Kardinal #1 — utuh secara konstruksi): usulan TIDAK PERNAH dieksekusi/dimuat;
ia hanya dokumen. Tool yang diusulkan TIDAK menjadi tersedia di lingkaran. Untuk benar-benar aktif,
MANUSIA harus: tinjau → tulis effector di organs/ → beri izin (granted_caps) di Peran. Otak tak bisa
menumbuhkan kuasa sendiri; ia hanya menaruh rancangan di meja manusia.
"""
from __future__ import annotations

from sadar.core.ports import ActionResult, EffectorSpec, ToolSpec
from sadar.organs.proposal_store import Proposal, ProposalStore


def _as_list(v) -> list[str]:
    if isinstance(v, list):
        return [str(x).strip() for x in v if str(x).strip()]
    if isinstance(v, str) and v.strip():
        return [v.strip()]
    return []


class ToolDraftEffector:
    def __init__(self, store: ProposalStore):
        self.store = store

    def list_tools(self) -> list[ToolSpec]:
        return [
            ToolSpec(name="tool_propose", reversible=True, side_effect="write",
                     required_caps=["tool.draft"],
                     usage=('args {"name":"web_fetch", "purpose":"untuk apa & mengapa diperlukan", '
                            '"required_caps":["web.read"], "code":"<rancangan kelas effector Python>", '
                            '"notes":"risiko, langkah wiring di build_sadar, izin yang perlu diberikan"}')),
            ToolSpec(name="tool_proposals", reversible=True, side_effect="read",
                     required_caps=["tool.draft"], usage='args {} — daftar usulan tool & status'),
        ]

    def act(self, tool: str, args: dict) -> ActionResult:
        cb = args.get("_caused_by", [])
        if tool == "tool_proposals":
            items = self.store.list()
            if not items:
                return ActionResult(tool=tool, ok=True, output="usulan tool: (belum ada)", caused_by=cb)
            txt = "; ".join(f"{p.name}[{p.status}]" for p in items)
            return ActionResult(tool=tool, ok=True, output="usulan tool: " + txt, caused_by=cb)

        if tool == "tool_propose":
            name = str(args.get("name", "")).strip()
            if not name:
                return ActionResult(tool=tool, ok=False, output="nama tool kosong", caused_by=cb)
            purpose = str(args.get("purpose", "")).strip()
            code = str(args.get("code", "")).strip()
            notes = str(args.get("notes", "")).strip()
            caps = _as_list(args.get("required_caps"))
            body = (
                f"## Tujuan\n{purpose or '[ISI:]'}\n\n"
                "## Rancangan kode (effector) — UNTUK DITINJAU MANUSIA, TIDAK dijalankan otomatis\n"
                f"```python\n{code or '[ISI: rancangan kode]'}\n```\n\n"
                f"## Izin yang diminta\n{', '.join(caps) or '[ISI:]'}\n\n"
                f"## Catatan untuk manusia (risiko & langkah wiring)\n{notes or '[ISI:]'}\n"
            )
            self.store.write(Proposal(name=name, description=purpose[:120],
                                      required_caps=caps, status="proposed", author="conversation", body=body))
            return ActionResult(
                tool=tool, ok=True, caused_by=cb,
                output=(f"usulan tool '{name}' disimpan sebagai DRAFT untuk ditinjau manusia. "
                        "Ini TIDAK aktif: butuh manusia mengimplementasi di organs/ + memberi izin di Peran."))

        return ActionResult(tool=tool, ok=False, output=f"tool tak dikenal: {tool}", caused_by=cb)

    def spec(self) -> EffectorSpec:
        return EffectorSpec(name="tool-draft", provenance="local", trust=1.0)
