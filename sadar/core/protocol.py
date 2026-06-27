"""Kontrak respons System-2 terstruktur + parser tahan-banting.

MENGAPA ADA: parsing teks-bebas `ACTION: tool {json}` lama (regex greedy + DOTALL)
over-capture prosa dan GAGAL-SENYAP (arg rusak → {} lalu aksi tetap jalan). Modul ini
menggantinya dengan ekstraksi JSON BERIMBANG (sadar-string) dan memisahkan dua hal:

  - self_state : KLAIM-DIRI terstruktur → diverifikasi KODE (bebas-bahasa) oleh Organ C.
  - action     : panggilan alat terstruktur → divalidasi terhadap registry tool.

DISIPLIN ANTI-FABRIKASI: bila respons tak dapat di-parse jadi aksi yang sah, kita TIDAK
menebak aksi — `action=None` + `parse_ok=False`. Engine lalu memperlakukannya sebagai
pikiran murni, bukan mengeksekusi tebakan. (Aturan Kardinal #1/#3/#6.)
"""
from __future__ import annotations

import json
import re
from typing import Any

from pydantic import BaseModel, Field


class ActionRequest(BaseModel):
    """Permintaan aksi MENTAH dari S2. Belum membawa kapabilitas — Engine yang mengisi
    reversible/affects_lifecycle dari ToolSpec (KODE), bukan dari LLM."""

    tool: str
    args: dict[str, Any] = Field(default_factory=dict)


class S2Response(BaseModel):
    """Hasil parse respons System-2."""

    reasoning: str = ""
    self_state: dict[str, Any] = Field(default_factory=dict)
    reply: str = ""                       # JAWABAN PERCAKAPAN (prosa) untuk pengguna — terpisah dari
                                          # 'action' (alat). Engine mengubahnya jadi ucapan, TETAP
                                          # melewati gerbang konstitusi (anti-fabrikasi tak dilonggarkan).
    action: ActionRequest | None = None
    parse_ok: bool = True
    parse_note: str = ""


_LEGACY_ACTION_RE = re.compile(r"ACTION:\s*([A-Za-z_]+)\s*(\{.*\})?", re.DOTALL)


def _extract_json_object(text: str) -> str | None:
    """Ambil objek JSON PERTAMA yang berimbang. Sadar-string (kurung di dalam string
    tak dihitung), jadi prosa setelah objek diabaikan dan '}' palsu tak menyesatkan.
    Mengganti regex greedy `{.*}` yang over-capture. Kembalikan None bila tak berimbang."""
    start = text.find("{")
    if start == -1:
        return None
    depth = 0
    in_str = False
    esc = False
    for i in range(start, len(text)):
        c = text[i]
        if in_str:
            if esc:
                esc = False
            elif c == "\\":
                esc = True
            elif c == '"':
                in_str = False
        elif c == '"':
            in_str = True
        elif c == "{":
            depth += 1
        elif c == "}":
            depth -= 1
            if depth == 0:
                return text[start : i + 1]
    return None  # kurung tak berimbang → bukan objek sah


def parse_s2_response(raw: str) -> S2Response:
    """Parse respons S2 → S2Response. Urutan: (1) JSON terstruktur berimbang [utama],
    (2) `ACTION: tool {json}` warisan [defense-in-depth], (3) pikiran murni tanpa aksi."""
    raw = raw or ""

    # (1) JALUR UTAMA — objek JSON terstruktur
    blob = _extract_json_object(raw)
    if blob is not None:
        try:
            data: Any = json.loads(blob)
        except json.JSONDecodeError:
            data = None
        if isinstance(data, dict) and any(k in data for k in ("action", "self_state", "reasoning", "reply")):
            action = None
            act = data.get("action")
            if isinstance(act, dict) and act.get("tool"):
                a_args = act.get("args")
                action = ActionRequest(
                    tool=str(act["tool"]),
                    args=a_args if isinstance(a_args, dict) else {},
                )
            ss = data.get("self_state")
            reply = data.get("reply")
            return S2Response(
                reasoning=str(data.get("reasoning", "")),
                self_state=ss if isinstance(ss, dict) else {},
                reply=str(reply) if isinstance(reply, str) else "",
                action=action,
                parse_ok=True,
            )

    # (2) JALUR WARISAN — `ACTION: tool {json}` di teks bebas
    m = _LEGACY_ACTION_RE.search(raw)
    if m:
        tool = m.group(1).strip()
        if m.group(2):
            arg_blob = _extract_json_object(m.group(2))
            try:
                parsed = json.loads(arg_blob) if arg_blob else None
            except json.JSONDecodeError:
                parsed = None
            if not isinstance(parsed, dict):
                # arg rusak → JANGAN tebak {}; tandai gagal-parse, JANGAN eksekusi (#6).
                return S2Response(
                    reasoning=raw, action=None, parse_ok=False,
                    parse_note=f"arg JSON tak-terparse untuk tool '{tool}'",
                )
            return S2Response(reasoning=raw, action=ActionRequest(tool=tool, args=parsed))
        return S2Response(reasoning=raw, action=ActionRequest(tool=tool, args={}))

    # (3) tak ada aksi → pikiran murni (jujur; tak ada aksi yang dikarang)
    return S2Response(reasoning=raw, action=None, parse_ok=True)
