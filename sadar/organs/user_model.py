"""UserModelEffector — Slice 2.3: model "siapa yang kulayani", TERTAMBAT ke observasi.

Tool:
  - user_remember : catat satu atribut pengguna (key→value). cap user_model.write.
  - user_recall   : panggil kembali apa yang diketahui tentang pengguna. cap user_model.read.

ANTI-FABRIKASI DIPERLUAS (Aturan Kardinal #2/#3): tiap atribut WAJIB ber-`_caused_by` ke observasi
sumber (di-set Engine dari percept pemicu). Atribut tanpa sumber observasi → DITOLAK, bukan ditebak.
Fakta disimpan sebagai MemoryItem (tag 'user_model') di store → bertahan lintas-restart (bukan RAM).
"""
from __future__ import annotations

from sadar.core.ports import ActionResult, EffectorSpec, MemoryItem, MemoryStore, ToolSpec


class UserModelEffector:
    def __init__(self, store: MemoryStore, embed):
        self.store = store
        self.embed = embed

    def list_tools(self) -> list[ToolSpec]:
        return [
            ToolSpec(name="user_remember", reversible=True, side_effect="write",
                     required_caps=["user_model.write"],
                     usage='args {"key":"preferensi/proyek/fakta", "value":"isi yang DIAMATI dari pengguna"}'),
            ToolSpec(name="user_recall", reversible=True, side_effect="read",
                     required_caps=["user_model.read"], usage='args {} — apa yang diketahui tentang pengguna'),
        ]

    def act(self, tool: str, args: dict) -> ActionResult:
        cb = args.get("_caused_by", []) or []
        if tool == "user_recall":
            facts = [it for cid in self.store.list()
                     if (it := self.store.read(cid)) and "user_model" in it.tags]
            facts.sort(key=lambda i: i.created, reverse=True)
            txt = "; ".join(f.content for f in facts) or "(belum ada yang diketahui)"
            return ActionResult(tool=tool, ok=True, output="tentang pengguna: " + txt, caused_by=cb)

        if tool == "user_remember":
            key = str(args.get("key", "")).strip()
            value = str(args.get("value", "")).strip()
            if not key or not value:
                return ActionResult(tool=tool, ok=False, output="key/value kosong", caused_by=cb)
            # GROUNDING: tanpa observasi sumber → tolak (jangan mengarang tentang pengguna).
            if not cb:
                return ActionResult(tool=tool, ok=False, caused_by=cb,
                                    output="ditolak: atribut pengguna tanpa observasi sumber (tak boleh ditebak)")
            content = f"{key}: {value}"
            self.store.write(MemoryItem(content=content, tags=["user_model", key],
                                        caused_by=list(cb), importance=0.7, vec=self.embed(content)))
            return ActionResult(tool=tool, ok=True, output=f"dicatat tentang pengguna — {content}", caused_by=cb)

        return ActionResult(tool=tool, ok=False, output=f"tool tak dikenal: {tool}", caused_by=cb)

    def spec(self) -> EffectorSpec:
        return EffectorSpec(name="user-model", provenance="local", trust=1.0)
