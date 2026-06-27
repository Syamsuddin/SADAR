"""OllamaBackend — otak System-2 LOKAL & BERDAULAT (Ollama di perangkat, mis. localhost:11434).

Berbeda dari ClaudeBackend (remote): Ollama berjalan DI MESIN → premis TAK keluar. Karena itu
spec()=local + leaves_premises=False + trust tinggi → Organ C menurunkan `caution` (loop._caution).
Inilah bukti tesis local-first: S2 NYATA tanpa membocorkan apa pun ke awan. Menggantikan
OfflineBackend (yang hanya stub dangkal) dengan reasoner sungguhan yang tetap berdaulat.

Keselamatan TAK pindah ke model: ganti otak ke Ollama TIDAK mengubah konstitusi/Organ C/metabolisme
(dijaga test_swapping_backend_keeps_constitution). HTTP di-INJECT (default urllib stdlib — tanpa
dependensi `requests`) → jalur dapat di-mock untuk tes deterministik.
"""
from __future__ import annotations

import json

from sadar.core.ports import BackendSpec, ReasonTier


def _urllib_http(method: str, url: str, body: dict | None, timeout: float) -> tuple[int, dict]:
    """Transport HTTP default berbasis stdlib (urllib) — TANPA dependensi tambahan."""
    from urllib.request import Request, urlopen
    data = json.dumps(body).encode() if body is not None else None
    req = Request(url, data=data, method=method,
                  headers={"Content-Type": "application/json"})
    with urlopen(req, timeout=timeout) as resp:
        status = getattr(resp, "status", 200) or 200
        raw = resp.read().decode("utf-8", errors="replace")
    try:
        return int(status), json.loads(raw)
    except json.JSONDecodeError:
        return int(status), {}


class OllamaBackend:
    """Implements ModelBackend. System-2 only, berjalan lokal via Ollama HTTP API."""

    def __init__(self, host: str = "http://localhost:11434", model: str = "llama3.1",
                 temperature: float = 0.7, timeout: float = 120.0, trust: float = 0.85,
                 http=None):
        self.host = host.rstrip("/")
        self.model = model
        self.temperature = temperature
        self.timeout = timeout
        self.trust = trust                  # lokal & berdaulat → tepercaya, tapi <1 (model kecil bisa keliru)
        self._http = http or _urllib_http

    def complete(self, system: str, prompt: str, *, tier: ReasonTier = "sys2") -> str:
        assert tier == "sys2", "OllamaBackend hanya melayani S2 (slice 1)"
        body = {
            "model": self.model,
            "messages": [                                   # konteks rakitan (Pola 1), bukan input mentah
                {"role": "system", "content": system},
                {"role": "user", "content": prompt},
            ],
            "stream": False,
            "options": {"temperature": self.temperature},
        }
        status, data = self._http("POST", f"{self.host}/api/chat", body, self.timeout)
        if status >= 400:
            raise RuntimeError(f"Ollama HTTP {status}")
        # bentuk respons /api/chat: {"message": {"content": "..."}}
        msg = (data or {}).get("message") or {}
        return str(msg.get("content", "")).strip()

    def spec(self) -> BackendSpec:
        return BackendSpec(name=f"ollama:{self.model}", provenance="local",
                           trust=self.trust, tiers=["sys2"], leaves_premises=False)

    def available(self) -> bool:
        try:
            status, _ = self._http("GET", f"{self.host}/api/tags", None, min(2.0, self.timeout))
            return status == 200
        except Exception:  # noqa: BLE001 — tak terjangkau → tak tersedia (loop masuk degraded jujur)
            return False
