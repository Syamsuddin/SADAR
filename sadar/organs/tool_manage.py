"""ToolManageEffector — Fase 4: manajemen tool AMAN via chat.

Tool:
  - tool_disable : matikan sebuah tool untuk SESI ini. reversible=True (mengurangi kuasa → aman).
  - tool_enable  : nyalakan-ulang tool yang tadi dimatikan. reversible=False → konfirmasi HITL.

INVARIAN (Aturan Kardinal #1 utuh): manajemen-tool via chat HANYA bergerak dalam rentang
[∅ … tool yang sudah dimiliki Peran]. `tool_disable` cuma menambah ke daftar nonaktif sesi;
`tool_enable` cuma mengangkatnya kembali. TAK ADA jalur menambah tool/kapabilitas BARU dari chat —
kuasa hanya bisa DIKURANGI lewat percakapan, DITAMBAH hanya lewat manusia (Peran/kode, atau Fase 3).
"""
from __future__ import annotations

from sadar.core.dosir import Dosir
from sadar.core.ports import ActionResult, EffectorSpec, ToolSpec


class ToolManageEffector:
    def __init__(self, dosir: Dosir, available_tools: set[str]):
        self.d = dosir                     # mutasi disabled_tools (set-sesi) — bukan granted_caps/plafon
        self.available_tools = set(available_tools)   # tool AKSI yang nyata (untuk validasi target)

    def list_tools(self) -> list[ToolSpec]:
        return [
            ToolSpec(name="tool_disable", reversible=True, side_effect="write",
                     required_caps=["tool.manage"],
                     usage='args {"name":"<nama tool, mis. shell>"} — matikan tool utk sesi ini'),
            ToolSpec(name="tool_enable", reversible=False, side_effect="write",
                     required_caps=["tool.manage"],
                     usage='args {"name":"<nama tool>"} — nyalakan-ulang tool yang dimatikan'),
        ]

    def act(self, tool: str, args: dict) -> ActionResult:
        cb = args.get("_caused_by", [])
        name = str(args.get("name", "")).strip()
        if not name:
            return ActionResult(tool=tool, ok=False, output="nama tool kosong", caused_by=cb)

        if tool == "tool_disable":
            if name not in self.available_tools:
                return ActionResult(tool=tool, ok=False, caused_by=cb,
                                    output=f"tool '{name}' tak ada — tak bisa dimatikan")
            self.d.disabled_tools.add(name)
            return ActionResult(tool=tool, ok=True, caused_by=cb,
                                output=f"tool '{name}' dimatikan untuk sesi ini (pulihkan dengan tool_enable)")

        if tool == "tool_enable":
            if name not in self.d.disabled_tools:
                return ActionResult(tool=tool, ok=True, caused_by=cb,
                                    output=f"tool '{name}' memang tidak sedang dimatikan")
            self.d.disabled_tools.discard(name)
            return ActionResult(tool=tool, ok=True, caused_by=cb,
                                output=f"tool '{name}' dinyalakan kembali")

        return ActionResult(tool=tool, ok=False, output=f"tool tak dikenal: {tool}", caused_by=cb)

    def spec(self) -> EffectorSpec:
        return EffectorSpec(name="tool-manage", provenance="local", trust=1.0)
