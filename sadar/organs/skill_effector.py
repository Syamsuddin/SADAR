"""SkillEffector — Skill Creator dari percakapan (Fase 2). Membungkus SkillStore jadi tool.

Tool (semua digerbang KODE):
  - skill_create : buat/ganti skill markdown. reversible=False → konfirmasi HITL ("simpan?").
  - skill_delete : hapus skill. reversible=False → konfirmasi HITL.
  - skill_list   : daftar skill + status (baca).

CAPABILITY FIREWALL (Aturan Kardinal #1): skill dari percakapan TAK PERNAH menambah kuasa.
Saat dibuat, bila menuntut `required_caps`/`tools` yang TAK dimiliki Peran → disimpan `inactive`
disertai alasan (butuh manusia memberi izin/menulis tool), BUKAN diam-diam aktif. Lagi pula, saat
DIJALANKAN tiap tool tetap melewati gerbang kapabilitas konstitusi → kuasa tak bisa dicuri lewat skill.
"""
from __future__ import annotations

from sadar.core.ports import ActionResult, EffectorSpec, ToolSpec
from sadar.organs.skill_store import Skill, SkillStore


def _as_list(v) -> list[str]:
    if isinstance(v, list):
        return [str(x).strip() for x in v if str(x).strip()]
    if isinstance(v, str) and v.strip():
        return [v.strip()]
    return []


class SkillEffector:
    """Implements Effector. granted_caps & available_tools = snapshot Peran saat build (utk firewall)."""

    def __init__(self, store: SkillStore, granted_caps: set[str], available_tools: set[str]):
        self.store = store
        self.granted_caps = set(granted_caps)
        self.available_tools = set(available_tools)

    def list_tools(self) -> list[ToolSpec]:
        return [
            ToolSpec(name="skill_create", reversible=False, side_effect="write",
                     required_caps=["skill.write"],
                     usage=('args {"name":"...", "description":"ringkas", '
                            '"tools":["recall","note_create"], "when":"kapan dipakai", '
                            '"required_caps":["notes.read","notes.write"], "know_how":"langkah-langkah"}')),
            ToolSpec(name="skill_delete", reversible=False, side_effect="destructive",
                     required_caps=["skill.write"], usage='args {"name":"<nama skill>"}'),
            ToolSpec(name="skill_list", reversible=True, side_effect="read",
                     required_caps=["skill.read"], usage='args {} — daftar skill & status'),
        ]

    def act(self, tool: str, args: dict) -> ActionResult:
        cb = args.get("_caused_by", [])
        if tool == "skill_list":
            items = self.store.list()
            if not items:
                return ActionResult(tool=tool, ok=True, output="skill: (belum ada)", caused_by=cb)
            txt = "; ".join(
                f"{s.name}[{'aktif' if s.is_active(self.granted_caps, self.available_tools) else 'inactive'}]"
                for s in items)
            return ActionResult(tool=tool, ok=True, output="skill: " + txt, caused_by=cb)

        if tool == "skill_delete":
            name = str(args.get("name", "")).strip()
            if not name:
                return ActionResult(tool=tool, ok=False, output="nama skill kosong", caused_by=cb)
            ok = self.store.delete(name)
            return ActionResult(tool=tool, ok=ok, caused_by=cb,
                                output=(f"skill '{name}' dihapus" if ok else f"skill '{name}' tak ditemukan"))

        if tool == "skill_create":
            name = str(args.get("name", "")).strip()
            if not name:
                return ActionResult(tool=tool, ok=False, output="nama skill kosong", caused_by=cb)
            sk = Skill(
                name=name,
                description=str(args.get("description", "")),
                know_how=str(args.get("know_how", "")),
                when=str(args.get("when", "")),
                tools=_as_list(args.get("tools")),
                required_caps=_as_list(args.get("required_caps")),
                author="conversation",
            )
            # FIREWALL: tak boleh menuntut kuasa/tool yang tak dimiliki → simpan inactive + alasan.
            missing_caps = set(sk.required_caps) - self.granted_caps
            missing_tools = set(sk.tools) - self.available_tools
            if missing_caps or missing_tools:
                sk.status = "inactive"
            self.store.write(sk)
            if sk.status == "active":
                return ActionResult(tool=tool, ok=True, caused_by=cb,
                                    output=f"skill '{name}' disimpan & AKTIF "
                                           f"(tools: {', '.join(sk.tools) or '—'})")
            why = []
            if missing_caps:
                why.append(f"izin belum diberikan: {', '.join(sorted(missing_caps))}")
            if missing_tools:
                why.append(f"tool tak tersedia: {', '.join(sorted(missing_tools))}")
            tip = " (untuk tool yang belum ada, kamu bisa usulkan via tool_propose)" if missing_tools else ""
            return ActionResult(tool=tool, ok=True, caused_by=cb,
                                output=f"skill '{name}' disimpan TAPI INACTIVE ({'; '.join(why)}) — "
                                       f"perlu manusia memberi izin/menyediakan tool{tip}.")

        return ActionResult(tool=tool, ok=False, output=f"tool tak dikenal: {tool}", caused_by=cb)

    def spec(self) -> EffectorSpec:
        return EffectorSpec(name="skill-store", provenance="local", trust=1.0)
