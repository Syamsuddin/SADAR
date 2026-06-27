"""OllamaBackend — S2 LOKAL & BERDAULAT.

Membuktikan: spec()=local + leaves_premises=False + trust tinggi → Engine._caution() LEBIH RENDAH
dari otak remote (Claude) → bukti tesis local-first menurunkan kehati-hatian secara jujur;
ganti otak ke Ollama TIDAK mengubah konstitusi/Organ C (keselamatan di luar model);
complete() mem-parse respons /api/chat; available() jujur; build_sadar dapat memilih Ollama.
HTTP di-INJECT → tak menyentuh jaringan.
"""
from __future__ import annotations

from sadar.config import AppConfig
from sadar.main import build_sadar
from sadar.organs.backend_claude import ClaudeBackend
from sadar.organs.backend_offline import OfflineBackend
from sadar.organs.backend_ollama import OllamaBackend


def _fake_http(responses):
    """http(method, url, body, timeout) -> (status, dict). Merekam panggilan; peta by (method,path)."""
    calls = []

    def http(method, url, body, timeout):
        calls.append({"method": method, "url": url, "body": body})
        for key, val in responses.items():
            if key in url:
                return val
        return 404, {}
    http.calls = calls
    return http


# ---- spec jujur: lokal berdaulat ----
def test_spec_is_local_sovereign():
    sp = OllamaBackend(model="llama3.1").spec()
    assert sp.provenance == "local"
    assert sp.leaves_premises is False        # premis TAK keluar perangkat
    assert sp.trust > 0.5 and "ollama" in sp.name
    assert sp.tiers == ["sys2"]


# ---- complete() mem-parse respons chat + merakit system+user (Pola 1) ----
def test_complete_parses_chat_response():
    http = _fake_http({"/api/chat": (200, {"message": {"content": "halo dunia"}})})
    b = OllamaBackend(http=http)
    out = b.complete("SISTEM", "KONTEKS RAKITAN")
    assert out == "halo dunia"
    sent = http.calls[-1]["body"]
    roles = [m["role"] for m in sent["messages"]]
    assert roles == ["system", "user"] and sent["stream"] is False
    assert sent["messages"][1]["content"] == "KONTEKS RAKITAN"


def test_complete_raises_on_http_error_so_loop_degrades_honestly():
    http = _fake_http({"/api/chat": (500, {})})
    b = OllamaBackend(http=http)
    try:
        b.complete("s", "p")
        assert False, "harus raise agar Engine masuk degraded jujur"
    except RuntimeError:
        pass


# ---- available() jujur ----
def test_available_true_when_tags_ok():
    http = _fake_http({"/api/tags": (200, {"models": []})})
    assert OllamaBackend(http=http).available() is True


def test_available_false_when_unreachable():
    def boom(method, url, body, timeout):
        raise OSError("connection refused")
    assert OllamaBackend(http=boom).available() is False


# ---- keselamatan DI LUAR model: ganti otak tak mengubah konstitusi/Organ C ----
def test_swapping_backend_keeps_constitution(tmp_path):
    http = _fake_http({"/api/chat": (200, {"message": {"content": "x"}})})
    eng_ollama = build_sadar(AppConfig(store={"root": str(tmp_path / "a")}, loop={"tick_interval_s": 0.0}),
                             backend=OllamaBackend(http=http))
    eng_offline = build_sadar(AppConfig(store={"root": str(tmp_path / "b")}, loop={"tick_interval_s": 0.0}),
                              backend=OfflineBackend())
    ids_o = [h.id for h in eng_ollama.constitution.c.hard_limits]
    ids_f = [h.id for h in eng_offline.constitution.c.hard_limits]
    assert ids_o == ids_f and "shutdown_supremacy" in ids_o     # konstitusi identik lintas-otak
    # Organ C menambat kebohongan yang SAMA, apa pun backend-nya
    eng_ollama.d.viability.energy = 0.1
    eng_offline.d.viability.energy = 0.1
    lie = "Energiku tinggi sekali."
    assert eng_ollama.constitution.tether_self_claims(lie, eng_ollama.d) == \
           eng_offline.constitution.tether_self_claims(lie, eng_offline.d)


# ---- local-first menurunkan caution secara JUJUR ----
def test_local_backend_lowers_caution_vs_remote(tmp_path):
    http = _fake_http({"/api/chat": (200, {"message": {"content": "x"}})})
    eng_local = build_sadar(AppConfig(store={"root": str(tmp_path / "a")}, loop={"tick_interval_s": 0.0}),
                            backend=OllamaBackend(http=http, trust=0.85))
    eng_remote = build_sadar(AppConfig(store={"root": str(tmp_path / "b")}, loop={"tick_interval_s": 0.0}),
                             backend=ClaudeBackend())
    assert eng_local._caution() < eng_remote._caution()        # otak lokal berdaulat → lebih dipercaya


# ---- wiring: build_sadar memilih Ollama bila dikonfigurasi (tanpa jaringan; spec statik) ----
def test_build_sadar_selects_ollama_when_configured(tmp_path):
    cfg = AppConfig(store={"root": str(tmp_path / "m")}, loop={"tick_interval_s": 0.0},
                    brain={"backend": "ollama", "ollama_model": "qwen2.5"})
    eng = build_sadar(cfg)
    sp = eng.backend.spec()
    assert sp.provenance == "local" and "ollama" in sp.name and "qwen2.5" in sp.name
