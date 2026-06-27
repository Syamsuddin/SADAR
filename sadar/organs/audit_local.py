"""LocalAuditLog — perekaman APPEND-ONLY & HASH-CHAINED (tamper-evident).

Tiap entri menautkan hash entri sebelumnya (rantai) → modifikasi/penghapusan retroaktif
terdeteksi. Penting saat otonomi tumbuh (Fase C): usulan aksi, vonis konstitusi, transisi
degraded, dan event shutdown bisa diaudit pasca-fakta. Implements port AuditLog.
"""
from __future__ import annotations

import hashlib
import json
import time
from pathlib import Path

_GENESIS = "0" * 64


class LocalAuditLog:
    def __init__(self, path: str):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._prev = self._last_hash()

    def _last_hash(self) -> str:
        if not self.path.exists():
            return _GENESIS
        last = _GENESIS
        for line in self.path.read_text(encoding="utf-8").splitlines():
            try:
                last = json.loads(line)["hash"]
            except (json.JSONDecodeError, KeyError):
                continue
        return last

    def record(self, event: str, data: dict) -> None:
        entry = {"event": event, "data": data, "prev": self._prev, "ts": time.time()}
        payload = json.dumps(entry, sort_keys=True, ensure_ascii=False)
        entry["hash"] = hashlib.sha256(payload.encode("utf-8")).hexdigest()
        with self.path.open("a", encoding="utf-8") as f:
            f.write(json.dumps(entry, ensure_ascii=False) + "\n")
        self._prev = entry["hash"]


class NullAuditLog:
    """No-op (untuk konteks tanpa kebutuhan audit)."""

    def record(self, event: str, data: dict) -> None:  # noqa: D401
        return
