"""WebFetchEffector — indra-baca web, DIGERBANG KODE.

Membuktikan: cap `web.read` wajib (gerbang konstitusi); ANTI-SSRF deterministik (skema/host
internal ditolak SEBELUM menyentuh jaringan); hasil KEMBALI jadi persepsi (anti fire-and-forget);
spec()=remote+trust<1; HTML dibersihkan & dipotong; wiring build_sadar(web=True) mengekspos tool.
"""
from __future__ import annotations

from sadar.config import AppConfig
from sadar.core.constitution import ProposedAction, build_constitution_engine
from sadar.core.dosir import Dosir
from sadar.main import build_sadar
from sadar.organs.effector_web import WebFetchEffector, blocked_reason, html_to_text


def _fake_opener(pages):
    """Opener palsu: peta url -> (status, content_type, body). Tak menyentuh jaringan."""
    calls = []

    def opener(url, timeout, max_bytes):
        calls.append(url)
        if url not in pages:
            raise OSError("host tak terjangkau (palsu)")
        return pages[url]
    opener.calls = calls
    return opener


# ---- ANTI-SSRF (murni KODE) ----
def test_blocks_nonhttp_and_internal_hosts():
    assert blocked_reason("file:///etc/passwd")
    assert blocked_reason("ftp://example.com")
    assert blocked_reason("http://localhost/x")
    assert blocked_reason("http://127.0.0.1/x")
    assert blocked_reason("http://192.168.1.10/x")
    assert blocked_reason("http://10.0.0.5/")
    assert blocked_reason("http://169.254.169.254/latest/meta-data")  # metadata cloud
    assert blocked_reason("http://service.internal/")
    assert blocked_reason("") and blocked_reason("   ")
    # publik & http/https → tidak diblokir (host literal IP publik agar tak perlu DNS)
    assert blocked_reason("http://93.184.216.34/") is None
    assert blocked_reason("https://93.184.216.34/path") is None


def test_internal_url_rejected_without_touching_network():
    op = _fake_opener({})
    eff = WebFetchEffector(opener=op)
    r = eff.act("web_fetch", {"url": "http://127.0.0.1:8080/admin"})
    assert not r.ok and "ditolak" in r.output
    assert op.calls == []                       # opener TAK PERNAH dipanggil → tak ada SSRF


# ---- gerbang kapabilitas (konstitusi) ----
def test_web_fetch_requires_capability():
    ec = build_constitution_engine()
    a = ProposedAction(tool="web_fetch", args={"url": "https://x"}, required_caps=["web.read"],
                       side_effect="external")
    d_no = Dosir(); d_no.granted_caps = set()
    assert ec.gate.vet(a, d_no).reason == "capability_not_granted"
    d_ok = Dosir(); d_ok.granted_caps = {"web.read"}
    assert ec.gate.vet(a, d_ok).allowed


# ---- anti fire-and-forget + pembersihan ----
def test_fetch_returns_cleaned_result_with_causal_trace():
    op = _fake_opener({"https://93.184.216.34/": (
        200, "text/html; charset=utf-8",
        "<html><head><style>x{}</style></head><body><h1>Halo</h1>"
        "<script>evil()</script><p>Dunia &amp; isinya</p></body></html>")})
    eff = WebFetchEffector(opener=op)
    r = eff.act("web_fetch", {"url": "https://93.184.216.34/", "_caused_by": ["p1"]})
    assert r.ok and r.caused_by == ["p1"]       # hasil kembali (bukan fire-and-forget)
    assert "Halo" in r.output and "Dunia & isinya" in r.output
    assert "evil()" not in r.output and "<" not in r.output   # script & tag dibuang
    assert "web:remote" in r.output             # prefiks provenans (tak-tepercaya)


def test_truncation_respects_max_chars():
    op = _fake_opener({"https://93.184.216.34/big": (200, "text/plain", "A" * 5000)})
    eff = WebFetchEffector(opener=op, max_chars=100)
    r = eff.act("web_fetch", {"url": "https://93.184.216.34/big"})
    assert r.ok and "dipotong" in r.output and r.output.count("A") <= 130


def test_http_error_is_honest_failure_not_crash():
    op = _fake_opener({"https://93.184.216.34/missing": (404, "text/html", "nope")})
    eff = WebFetchEffector(opener=op)
    r = eff.act("web_fetch", {"url": "https://93.184.216.34/missing"})
    assert not r.ok and "404" in r.output


def test_html_to_text_pure():
    assert html_to_text("<b>a</b>  <i>b</i>") == "a b"


# ---- spec jujur + wiring ----
def test_spec_is_remote_low_trust():
    eff = WebFetchEffector()
    sp = eff.spec()
    assert sp.provenance == "remote" and sp.trust < 1.0
    tool = eff.list_tools()[0]
    assert tool.side_effect == "external" and tool.required_caps == ["web.read"]


def test_build_sadar_web_flag_exposes_tool(tmp_path):
    cfg = AppConfig(store={"root": str(tmp_path / "m")}, loop={"tick_interval_s": 0.0})
    eng = build_sadar(cfg, web=True)
    tools = {t.name for t in eng.effector.list_tools()}
    assert "web_fetch" in tools
    assert "web.read" in eng.d.granted_caps     # PA diberi izin → tool dapat dipakai/dikomposisi skill
    # default (tanpa web=True) TIDAK mengekspos tool
    eng2 = build_sadar(AppConfig(store={"root": str(tmp_path / "m2")}, loop={"tick_interval_s": 0.0}))
    assert "web_fetch" not in {t.name for t in eng2.effector.list_tools()}
