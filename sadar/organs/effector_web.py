"""WebFetchEffector — tangan BACA-WEB: ambil isi sebuah URL (read-only), DIGERBANG KODE.

Adapter (nol perubahan core/). Memberi SADAR "indra-baca dunia" lewat SATU tool:
  - tool 'web_fetch' : unduh & bersihkan isi URL → teks. reversible=True, side_effect='external'.

KEAMANAN (semua di KODE, bukan ditimbang LLM — Aturan Kardinal #1):
  - kapabilitas wajib `web.read` (gerbang konstitusi).
  - ANTI-SSRF deterministik: hanya skema http/https; tolak host lokal/privat/link-local/loopback
    (mis. localhost, 127.x, 10.x, 192.168.x, 169.254.169.254) → cegah otak menyentuh jaringan-dalam.
  - batas ukuran unduh + timeout; HTML dibersihkan jadi teks lalu dipotong.
Hasil unduhan KEMBALI jadi persepsi (anti fire-and-forget). Karena jaringan REMOTE & tak-tepercaya,
spec()=remote+trust<1 dan output DIBERI PREFIKS provenans → Organ C/konteks memperlakukannya hati-hati.

`opener` di-INJECT (default = urllib stdlib, tanpa dependensi) → jalur dapat di-mock untuk tes.
"""
from __future__ import annotations

import html
import ipaddress
import re
import socket
from urllib.parse import urlparse

from sadar.core.ports import ActionResult, EffectorSpec, ToolSpec

_TAG_RE = re.compile(r"<(script|style)[^>]*>.*?</\1>", re.DOTALL | re.IGNORECASE)
_ANY_TAG = re.compile(r"<[^>]+>")
_WS = re.compile(r"[ \t\r\f\v]+")
_NL = re.compile(r"\n\s*\n\s*\n+")
# host yang JELAS internal (selain literal IP yang diperiksa via ipaddress).
_BLOCK_HOSTS = {"localhost", "ip6-localhost", "ip6-loopback"}
_BLOCK_SUFFIX = (".local", ".internal", ".localhost")


def _host_is_internal(host: str) -> bool:
    """True bila host menunjuk ke jaringan-dalam/loopback/link-local. DETERMINISTIK, KODE."""
    h = (host or "").strip().strip("[]").lower()
    if not h or h in _BLOCK_HOSTS or h.endswith(_BLOCK_SUFFIX):
        return True
    # literal IP → periksa langsung
    try:
        ip = ipaddress.ip_address(h)
        return ip.is_private or ip.is_loopback or ip.is_link_local or ip.is_reserved or ip.is_unspecified
    except ValueError:
        pass
    # nama host → resolusi best-effort lalu periksa SEMUA alamat (cegah rebinding sederhana).
    try:
        infos = socket.getaddrinfo(h, None)
    except (OSError, UnicodeError):
        return False     # tak bisa resolusi → biarkan opener yang gagal jujur (bukan blokir buta)
    for info in infos:
        addr = info[4][0]
        try:
            ip = ipaddress.ip_address(addr.split("%", 1)[0])
        except ValueError:
            continue
        if ip.is_private or ip.is_loopback or ip.is_link_local or ip.is_reserved or ip.is_unspecified:
            return True
    return False


def blocked_reason(url: str, *, allow_private: bool = False) -> str | None:
    """Kembalikan ALASAN blokir (str) atau None bila URL boleh diambil. MURNI KODE, bebas-LLM."""
    u = (url or "").strip()
    if not u:
        return "url kosong"
    p = urlparse(u)
    if p.scheme.lower() not in ("http", "https"):
        return f"skema '{p.scheme or '?'}' tak diizinkan (hanya http/https)"
    if not p.hostname:
        return "host kosong"
    if not allow_private and _host_is_internal(p.hostname):
        return f"host internal/privat diblokir: {p.hostname}"
    return None


def html_to_text(body: str) -> str:
    """Bersihkan HTML → teks terbaca (deterministik): buang script/style, tanggalkan tag, rapikan."""
    s = _TAG_RE.sub(" ", body)
    s = _ANY_TAG.sub(" ", s)
    s = html.unescape(s)
    s = _WS.sub(" ", s)
    s = _NL.sub("\n\n", s)
    return s.strip()


def _urllib_opener(url: str, timeout: float, max_bytes: int) -> tuple[int, str, str]:
    """Opener default berbasis stdlib (urllib) — TANPA dependensi tambahan."""
    from urllib.request import Request, urlopen
    req = Request(url, headers={"User-Agent": "SADAR/0.1 (+local agent; read-only)"})
    with urlopen(req, timeout=timeout) as resp:        # nosec - skema/host sudah disaring KODE
        status = getattr(resp, "status", 200) or 200
        ctype = resp.headers.get("Content-Type", "") if resp.headers else ""
        raw = resp.read(max_bytes + 1)
    charset = "utf-8"
    m = re.search(r"charset=([\w-]+)", ctype, re.IGNORECASE)
    if m:
        charset = m.group(1)
    text = raw.decode(charset, errors="replace")
    return int(status), ctype, text


class WebFetchEffector:
    """Implements Effector. opener(url, timeout, max_bytes)->(status, content_type, body)."""

    def __init__(self, opener=None, timeout: float = 15.0, max_bytes: int = 200_000,
                 max_chars: int = 2000, allow_private: bool = False, trust: float = 0.6):
        self.opener = opener or _urllib_opener
        self.timeout = timeout
        self.max_bytes = max_bytes
        self.max_chars = max_chars
        self.allow_private = allow_private
        self.trust = trust

    def list_tools(self) -> list[ToolSpec]:
        return [ToolSpec(
            name="web_fetch", reversible=True, side_effect="external",
            provenance="remote", trust=self.trust, required_caps=["web.read"],
            usage='args {"url": "https://...", "max_chars": 2000} — baca isi sebuah halaman web')]

    def act(self, tool: str, args: dict) -> ActionResult:
        cb = args.get("_caused_by", [])
        if tool != "web_fetch":
            return ActionResult(tool=tool, ok=False, output=f"tool tak dikenal: {tool}", caused_by=cb)
        url = str(args.get("url", "")).strip()
        reason = blocked_reason(url, allow_private=self.allow_private)
        if reason is not None:
            return ActionResult(tool=tool, ok=False, output=f"ditolak: {reason}", caused_by=cb)
        max_chars = int(args.get("max_chars", self.max_chars) or self.max_chars)
        try:
            status, ctype, body = self.opener(url, self.timeout, self.max_bytes)
        except Exception as e:  # noqa: BLE001 — kegagalan jaringan → hasil jujur, bukan crash loop
            return ActionResult(tool=tool, ok=False, output=f"galat ambil '{url}': {e}", caused_by=cb)
        if status >= 400:
            return ActionResult(tool=tool, ok=False, output=f"HTTP {status} dari {url}", caused_by=cb)
        text = html_to_text(body) if "html" in (ctype or "").lower() or "<" in body[:512] else body.strip()
        truncated = len(text) > max_chars
        if truncated:
            text = text[:max_chars] + f"\n…[dipotong, total {len(text)} char]"
        # PREFIKS provenans: tegaskan isi BERASAL dari web remote & tak-tepercaya (bukan klaim-diri).
        out = f"[web:remote trust={self.trust}] {url}\n{text}" if text else f"[web:remote] {url} (kosong)"
        return ActionResult(tool=tool, ok=True, output=out, caused_by=cb)

    def spec(self) -> EffectorSpec:
        return EffectorSpec(name="web-fetch", provenance="remote", trust=self.trust)
