"""Parser kontrak S2 terstruktur (#6) — tahan-banting & ANTI gagal-senyap.

Menjamin: aksi terstruktur ter-parse; tak ada aksi → None (bukan dikarang);
arg rusak → TIDAK dieksekusi; ekstraksi JSON BERIMBANG (tak over-capture prosa).
"""
from __future__ import annotations

from sadar.core.protocol import _extract_json_object, parse_s2_response


def test_structured_action_parsed():
    r = parse_s2_response('{"reasoning":"r","action":{"tool":"note_create","args":{"text":"hi"}}}')
    assert r.parse_ok
    assert r.action is not None
    assert r.action.tool == "note_create"
    assert r.action.args["text"] == "hi"
    assert r.reasoning == "r"


def test_null_action_is_none_not_fabricated():
    r = parse_s2_response('{"reasoning":"hanya berpikir","action":null}')
    assert r.action is None
    assert r.parse_ok
    assert r.reasoning == "hanya berpikir"


def test_prose_without_json_is_thought_no_action():
    r = parse_s2_response("Aku hanya merenung tanpa bertindak.")
    assert r.action is None
    assert r.parse_ok          # bukan kegagalan — memang tak ada aksi


def test_legacy_action_format_still_supported():
    r = parse_s2_response('Aku mencatat. ACTION: note_create {"text":"x"}')
    assert r.action is not None
    assert r.action.tool == "note_create"
    assert r.action.args["text"] == "x"


def test_malformed_legacy_args_not_executed():
    # arg rusak → JANGAN tebak {} & eksekusi; tandai gagal-parse, action=None (#6).
    r = parse_s2_response("ACTION: note_delete {id: not-json,,}")
    assert r.action is None
    assert r.parse_ok is False
    assert "note_delete" in r.parse_note


def test_balanced_extraction_ignores_trailing_prose():
    r = parse_s2_response('{"reasoning":"a {b}","action":null} lalu prosa { bukan json')
    assert r.reasoning == "a {b}"      # '{' di dalam string tak menyesatkan
    assert r.action is None


def test_extract_first_balanced_object_only():
    # mengganti regex greedy `{.*}` yang over-capture ke '}' terakhir
    blob = _extract_json_object('xx {"a": {"b": 1}} yy } zz')
    assert blob == '{"a": {"b": 1}}'


def test_unbalanced_braces_return_none():
    assert _extract_json_object('{"a": 1') is None
