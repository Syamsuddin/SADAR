"""Kanal Telegram — sepasang organ: TelegramPerceiver (pesan masuk) + TelegramEffector (kirim).

Bukti tesis buta-platform: kanal nyata, NOL perubahan sadar/core/. Pesan masuk jadi
Representation(source='perception') → dirakit ke konteks (Pola 1), BUKAN prompt mentah → tahan-injeksi.
Ucapan keluar lewat tool 'send_message' (side_effect='external') → otomatis digerbang anti-fabrikasi
oleh konstitusi (SADAR boleh kirim pesan, tak boleh berbohong soal dirinya).

PAIRING (default-deny, roadmap 4.3): pengirim TAK dikenal DIABAIKAN — identitas/izin di KODE, bukan
prompt. Hanya `owner_ids` (allowlist) atau pengirim yang mengirim `pairing_code` benar yang diproses.
Inilah keamanan-skala-jangkauan: memperluas kanal TIDAK memperluas siapa yang boleh menyuruh SADAR.

`transport` di-INJECT (default HTTP via urllib stdlib — tanpa dependensi) → dapat di-mock untuk tes.
Kanal REMOTE → spec() trust<1 + leaves_premises=True → Organ C lebih hati-hati.
"""
from __future__ import annotations

import json

from sadar.core.dosir import Representation
from sadar.core.ports import ActionResult, EffectorSpec, PerceiverSpec, ToolSpec

_API = "https://api.telegram.org"


class HttpTelegramTransport:
    """Transport Bot API berbasis urllib stdlib. poll()=getUpdates, send()=sendMessage."""

    def __init__(self, token: str, timeout: float = 20.0):
        self.token = token
        self.timeout = timeout
        self._offset = 0

    def _call(self, method: str, params: dict) -> dict:
        from urllib.parse import urlencode
        from urllib.request import urlopen
        url = f"{_API}/bot{self.token}/{method}?{urlencode(params)}"
        with urlopen(url, timeout=self.timeout) as resp:       # nosec - host API tetap (bukan dari LLM)
            return json.loads(resp.read().decode("utf-8", errors="replace"))

    def poll(self) -> list[tuple[int, str]]:
        data = self._call("getUpdates", {"offset": self._offset, "timeout": 0})
        out: list[tuple[int, str]] = []
        for upd in data.get("result", []):
            self._offset = max(self._offset, int(upd.get("update_id", 0)) + 1)
            msg = upd.get("message") or {}
            chat = (msg.get("chat") or {}).get("id")
            text = msg.get("text")
            if chat is not None and text:
                out.append((int(chat), str(text)))
        return out

    def send(self, chat_id: int, text: str) -> bool:
        data = self._call("sendMessage", {"chat_id": chat_id, "text": text})
        return bool(data.get("ok"))


class TelegramPerceiver:
    """Implements Perceiver. MULTI-USER (4.3): banyak pengirim, masing-masing beridentitas & berlevel.
      - owner (allowlist `owner_ids`) & guest (ter-pairing via kode) → diproses, ditandai asalnya.
      - pengirim TAK dikenal → DIABAIKAN (default-deny) — identitas/izin di KODE, bukan prompt.
    Tiap pesan menyetel `reply_state['reply_to']` → balasan default kembali ke PENGIRIM yang tepat."""

    def __init__(self, transport, owner_ids=(), pairing_code: str | None = None,
                 trust: float = 0.7, emit_clock: bool = False, allow_guests: bool = True,
                 reply_state: dict | None = None):
        self.transport = transport
        self.owners: set[int] = {int(x) for x in owner_ids}
        self.guests: set[int] = set()
        self.paired: set[int] = set(self.owners)   # authorized = owners ∪ guests (kompat lama)
        self.pairing_code = pairing_code
        self.trust = trust
        self.emit_clock = emit_clock            # default OFF: detak dipasok indra lokal (cegah dobel)
        self.allow_guests = allow_guests        # bila False → hanya owner; kode pairing diabaikan
        self.reply_state = reply_state          # dibagi dgn effector → routing balasan ke pengirim

    def level(self, chat_id: int) -> str | None:
        """Level akses pengirim: 'owner' | 'guest' | None (tak dikenal → diabaikan)."""
        if chat_id in self.owners:
            return "owner"
        if chat_id in self.guests:
            return "guest"
        return None

    def poll(self) -> list[Representation]:
        out: list[Representation] = []
        if self.emit_clock:
            import time
            out.append(Representation(content=f"[tik] waktu={time.time():.0f}",
                                      source="perception", trust=1.0, ephemeral=True))
        for chat_id, text in self.transport.poll():
            lvl = self.level(chat_id)
            if lvl is not None:
                if self.reply_state is not None:
                    self.reply_state["reply_to"] = chat_id     # balas ke pengirim ini (routing)
                # prefiks "pesan pengguna:" DIPERTAHANKAN (kontrak lintas-kode); identitas jadi sufiks.
                out.append(Representation(content=f"pesan pengguna: {text} [dari {lvl}:{chat_id}]",
                                          source="perception", trust=self.trust))
            elif self.allow_guests and self.pairing_code and text.strip() == self.pairing_code:
                self.guests.add(chat_id)         # PAIRING via KODE (bukan ditafsir LLM) → jadi GUEST
                self.paired.add(chat_id)
                out.append(Representation(
                    content=f"[PAIRING] pengirim {chat_id} dipasangkan sebagai guest.", source="thought"))
            # else: pengirim tak dikenal → DIABAIKAN (default-deny). Tak masuk kesadaran sama sekali.
        return out

    def spec(self) -> PerceiverSpec:
        return PerceiverSpec(name="telegram", provenance="remote", trust=self.trust,
                             leaves_premises=True)


class TelegramEffector:
    """Implements Effector. tool 'send_message' (external → digerbang anti-fabrikasi konstitusi)."""

    def __init__(self, transport, default_chat_id: int | None = None, trust: float = 0.7,
                 reply_state: dict | None = None):
        self.transport = transport
        self.default_chat_id = default_chat_id
        self.trust = trust
        self.reply_state = reply_state          # multi-user: balas ke pengirim terakhir bila chat_id absen

    def list_tools(self) -> list[ToolSpec]:
        return [ToolSpec(
            name="send_message", reversible=True, side_effect="external",
            provenance="remote", trust=self.trust, required_caps=["channel.send"],
            usage='args {"text": "isi pesan", "chat_id": <opsional; default ke pemilik>}')]

    def act(self, tool: str, args: dict) -> ActionResult:
        cb = args.get("_caused_by", [])
        if tool != "send_message":
            return ActionResult(tool=tool, ok=False, output=f"tool tak dikenal: {tool}", caused_by=cb)
        text = str(args.get("text") or args.get("message") or args.get("content") or "").strip()
        if not text:
            return ActionResult(tool=tool, ok=False, output="teks kosong", caused_by=cb)
        # routing balasan: chat_id eksplisit > pengirim terakhir (reply_state) > default (pemilik).
        chat_id = args.get("chat_id")
        if chat_id is None and self.reply_state is not None:
            chat_id = self.reply_state.get("reply_to")
        if chat_id is None:
            chat_id = self.default_chat_id
        if chat_id is None:
            return ActionResult(tool=tool, ok=False,
                                output="chat_id tak diketahui (belum ada pemilik/pairing)", caused_by=cb)
        try:
            ok = bool(self.transport.send(int(chat_id), text))
        except Exception as e:  # noqa: BLE001 — gagal kirim → hasil jujur, bukan crash loop
            return ActionResult(tool=tool, ok=False, output=f"galat kirim: {e}", caused_by=cb)
        return ActionResult(tool=tool, ok=ok, caused_by=cb,
                            output=(f"[terkirim→{chat_id}] {text}" if ok else "gagal kirim (API menolak)"))

    def spec(self) -> EffectorSpec:
        return EffectorSpec(name="telegram", provenance="remote", trust=self.trust)


def make_telegram_channel(token: str, owner_ids=(), pairing_code: str | None = None,
                          default_chat_id: int | None = None, trust: float = 0.7):
    """Konstruksi sepasang (Perceiver, Effector) Telegram berbagi satu transport HTTP.
    Dipakai: build_sadar(channels=list(make_telegram_channel(token, owner_ids=[123])))."""
    transport = HttpTelegramTransport(token)
    if default_chat_id is None and owner_ids:
        default_chat_id = int(next(iter(owner_ids)))
    state = {"reply_to": default_chat_id}        # dibagi → balasan default mengikuti pengirim terakhir
    perceiver = TelegramPerceiver(transport, owner_ids=owner_ids, pairing_code=pairing_code,
                                  trust=trust, reply_state=state)
    effector = TelegramEffector(transport, default_chat_id=default_chat_id, trust=trust, reply_state=state)
    return perceiver, effector
