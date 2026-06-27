"""ClaudeBackend — otak System-2 via Anthropic API (Sonnet 4.6).

Import anthropic bersifat LAZY → paket tetap dapat diimpor & diuji tanpa SDK/API key.
Pola 1: 'prompt' adalah KONTEKS RAKITAN dari Dosir, bukan masukan mentah pengguna.
spec(): remote, trust rendah, leaves_premises=True → Organ C menaikkan kehati-hatian.
"""
from __future__ import annotations

import os

from sadar.core.ports import BackendSpec, ReasonTier


class ClaudeBackend:
    """Implements ModelBackend. System-2 only."""

    def __init__(self, model: str = "claude-sonnet-4-6", max_tokens: int = 2048,
                 temperature: float = 0.7):
        self.model = model
        self.max_tokens = max_tokens
        self.temperature = temperature      # variasi gaya jawaban (Pola 1 tetap: konteks rakitan)
        self._client = None

    def _ensure(self):
        if self._client is None:
            from anthropic import Anthropic  # lazy
            self._client = Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])
        return self._client

    def complete(self, system: str, prompt: str, *, tier: ReasonTier = "sys2") -> str:
        assert tier == "sys2", "ClaudeBackend hanya melayani S2 (slice 1)"
        client = self._ensure()
        msg = client.messages.create(
            model=self.model, max_tokens=self.max_tokens, temperature=self.temperature,
            system=system,
            messages=[{"role": "user", "content": prompt}],   # konteks rakitan, bukan input mentah
        )
        return "".join(b.text for b in msg.content if getattr(b, "type", None) == "text")

    def spec(self) -> BackendSpec:
        return BackendSpec(name="claude-sonnet-4.6", provenance="remote",
                           trust=0.5, tiers=["sys2"], leaves_premises=True)

    def available(self) -> bool:
        if not os.environ.get("ANTHROPIC_API_KEY"):
            return False
        try:
            import anthropic  # noqa: F401
            return True
        except Exception:
            return False
