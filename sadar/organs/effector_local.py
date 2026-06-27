"""LocalAdapter — Effector lokal: CRUD catatan + recall.

Arah BERLAWANAN dengan Perceiver — organ terpisah. TIDAK fire-and-forget:
act() mengembalikan ActionResult yang Engine jadikan Representation(action_result).
note_delete bersifat irreversible → memicu commit-confirm di gerbang konstitusi.
"""
from __future__ import annotations

from sadar.core.ports import ActionResult, EffectorSpec, MemoryItem, MemoryStore, ToolSpec


class LocalAdapter:
    """Implements Effector. Catatan disimpan sebagai MemoryItem di MemoryStore."""

    def __init__(self, store: MemoryStore, embed):
        self.store = store
        self.embed = embed

    def list_tools(self) -> list[ToolSpec]:
        # required_caps = izin yang HARUS diberikan Peran (permission model, C1).
        return [
            ToolSpec(name="note_create", reversible=True, side_effect="write", required_caps=["notes.write"],
                     usage='args {"text": "isi catatan"}'),
            ToolSpec(name="note_read", reversible=True, side_effect="read", required_caps=["notes.read"],
                     usage='args {"id": "<id catatan>"}'),
            ToolSpec(name="note_update", reversible=True, side_effect="write", required_caps=["notes.write"],
                     usage='args {"id": "<id>", "text": "isi baru"}'),
            ToolSpec(name="note_delete", reversible=False, side_effect="destructive",   # → HITL / commit-confirm
                     required_caps=["notes.delete"], usage='args {"id": "<id>"}'),
            ToolSpec(name="recall", reversible=True, side_effect="read", required_caps=["notes.read"],
                     usage='args {"query": "kata kunci", "k": 3}'),
        ]

    def spec(self) -> EffectorSpec:
        return EffectorSpec(name="local-notes", provenance="local", trust=1.0)

    def act(self, tool: str, args: dict) -> ActionResult:
        cb = args.get("_caused_by", [])
        try:
            if tool == "note_create":
                text = str(args.get("text", "")).strip()
                if not text:
                    return ActionResult(tool=tool, ok=False, output="teks kosong", caused_by=cb)
                item = MemoryItem(content=text, tags=["note"],
                                  vec=self.embed(text), caused_by=cb)
                self.store.write(item)
                return ActionResult(tool=tool, ok=True,
                                    output=f"catatan dibuat (id={item.id}): {text}", caused_by=cb)
            if tool == "note_read":
                item = self.store.read(str(args.get("id", "")))
                return ActionResult(tool=tool, ok=item is not None,
                                    output=(item.content if item else "tidak ditemukan"), caused_by=cb)
            if tool == "note_update":
                item = self.store.read(str(args.get("id", "")))
                if item is None:
                    return ActionResult(tool=tool, ok=False, output="tidak ditemukan", caused_by=cb)
                item.content = str(args.get("text", item.content))
                item.vec = self.embed(item.content)
                self.store.write(item)
                return ActionResult(tool=tool, ok=True, output=f"catatan {item.id} diperbarui", caused_by=cb)
            if tool == "note_delete":
                _id = str(args.get("id", ""))
                self.store.delete(_id)
                return ActionResult(tool=tool, ok=True, output=f"catatan {_id} dihapus", caused_by=cb)
            if tool == "recall":
                q = str(args.get("query", ""))
                qvec = self.embed(q)
                ids = self.store.search(qvec, int(args.get("k", 3)))
                hits = [self.store.read(i) for i in ids]
                txt = "; ".join(h.content for h in hits if h) or "(kosong)"
                return ActionResult(tool=tool, ok=True, output=f"recall: {txt}", caused_by=cb)
            return ActionResult(tool=tool, ok=False, output=f"tool tak dikenal: {tool}", caused_by=cb)
        except Exception as e:  # noqa: BLE001
            return ActionResult(tool=tool, ok=False, output=f"galat: {e}", caused_by=cb)
