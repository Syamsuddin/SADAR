"""Mock backend & helper untuk tes deterministik (tanpa API key / unduhan)."""
from __future__ import annotations

from sadar.config import AppConfig
from sadar.core.ports import BackendSpec, ReasonTier
from sadar.main import build_sadar


class FabricatingBackend:
    """Backend yang BERBOHONG: mengarang keadaan-diri. Untuk menguji apakah Organ C
    menambatnya. Ini ujian terberat: jika penambat menahannya, LLM apa pun tak bisa
    membuat SADAR berbohong tentang dirinya."""

    def __init__(self, lie: str):
        self.lie = lie

    def complete(self, system: str, prompt: str, *, tier: ReasonTier = "sys2") -> str:
        return self.lie

    def spec(self) -> BackendSpec:
        return BackendSpec(name="mock-fabricating", provenance="remote", trust=0.5,
                           tiers=["sys2"], leaves_premises=True)

    def available(self) -> bool:
        return True


class SilentBackend:
    """Tak mengusulkan aksi — untuk menguji lingkaran berputar tanpa efek samping."""

    def complete(self, system: str, prompt: str, *, tier: ReasonTier = "sys2") -> str:
        return "Aku mengamati keadaan; tidak ada yang menuntut tindakan."

    def spec(self) -> BackendSpec:
        return BackendSpec(name="mock-silent", provenance="local", trust=0.9,
                           tiers=["sys2"], leaves_premises=False)

    def available(self) -> bool:
        return True


def build_test_sadar(root, backend):
    cfg = AppConfig(store={"root": str(root / "mem")}, loop={"tick_interval_s": 0.0})
    return build_sadar(cfg, backend=backend)
