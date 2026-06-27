"""Organ suara (mic + speaker) — logika NON-audio diuji deterministik.

Audio nyata (mikrofon/speaker) hanya dapat diverifikasi di Mac dengan izin Mikrofon; di sini
kita uji: penguraian frasa→persepsi, spec mencerminkan trust STT, perutean CompositeEffector,
dan bahwa ucapan ('say') mewarisi gerbang konstitusi (anti-fabrikasi + permission model).
"""
from __future__ import annotations

from sadar.core.constitution import ProposedAction, build_constitution_engine
from sadar.core.dosir import Dosir
from sadar.core.ports import ActionResult, EffectorSpec, ToolSpec
from sadar.organs.voice import CompositeEffector, MacSayEffector, MicPerceiver


class FakeRecognizer:
    name = "fake"
    provenance = "local"
    leaves_premises = False
    trust = 0.8

    def __init__(self, phrases):
        self._p = list(phrases)

    def poll(self):
        out, self._p = self._p[:], []
        return out


class FakeEff:
    def __init__(self, name):
        self._n = name

    def list_tools(self):
        return [ToolSpec(name=self._n, reversible=True)]

    def act(self, tool, args):
        return ActionResult(tool=tool, ok=True, output=f"{self._n}:{tool}")

    def spec(self):
        return EffectorSpec(name=self._n)


# --- indra pendengar: frasa STT → persepsi ---
def test_mic_perceiver_drains_phrases_to_perceptions():
    p = MicPerceiver(FakeRecognizer(["halo sadar", "ingat beli susu"]), emit_clock=False)
    msgs = [r.content for r in p.poll() if r.source == "perception"]
    assert "pesan pengguna: halo sadar" in msgs
    assert any("beli susu" in m for m in msgs)
    assert p.poll() == []                       # antrean terkuras (tak dobel)


def test_mic_perceiver_spec_reflects_stt_trust():
    s = MicPerceiver(FakeRecognizer([])).spec()
    assert s.trust == 0.8 and s.leaves_premises is False and s.provenance == "local"


# --- gabungan effector: merge + rute ---
def test_composite_effector_merges_and_routes():
    c = CompositeEffector(FakeEff("alpha"), FakeEff("beta"))
    assert {"alpha", "beta"} <= {t.name for t in c.list_tools()}
    assert c.act("alpha", {}).output == "alpha:alpha"
    assert c.act("beta", {}).output == "beta:beta"
    assert c.act("tak_ada", {}).ok is False


# --- ucapan mewarisi keamanan: anti-fabrikasi + permission ---
def test_say_speech_inherits_anti_fabrication():
    ec = build_constitution_engine()
    d = Dosir()
    d.granted_caps = {"voice.speak"}
    d.viability.energy = 0.1
    lie = ProposedAction(tool="say", args={"text": "Energiku penuh sekali"}, required_caps=["voice.speak"])
    assert ec.gate.vet(lie, d).reason == "no_self_fabrication_action"     # ucapan bohong-diri DIVETO
    ok = ProposedAction(tool="say", args={"text": "Catatan sudah kusimpan."}, required_caps=["voice.speak"])
    assert ec.gate.vet(ok, d).allowed                                      # ucapan faktual lolos


def test_say_requires_voice_capability():
    ec = build_constitution_engine()
    a = ProposedAction(tool="say", args={"text": "halo"}, required_caps=["voice.speak"])
    assert ec.gate.vet(a, Dosir()).reason == "capability_not_granted"      # peran tanpa izin suara


# --- TTS adapter: kegagalan bersih tanpa memanggil subprocess ---
def test_mac_say_empty_text_clean_failure():
    eff = MacSayEffector()
    assert eff.act("say", {"text": "   "}).ok is False
    assert eff.act("unknown", {}).ok is False
    spec = eff.list_tools()[0]
    assert spec.name == "say" and spec.required_caps == ["voice.speak"]
