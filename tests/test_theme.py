"""Windows 95 HTML builders: balanced markup, nothing loaded from outside, and every source-supplied value escaped."""

import re
from datetime import datetime

import pytest

import render
import theme

HOSTILE = ["<script>alert(1)</script>", '"><img src=x onerror=alert(1)>', "<b>bold</b>", "</div><div>"]


def balanced(html_text: str) -> bool:
    return len(re.findall(r"<div\b", html_text)) == len(re.findall(r"</div>", html_text))


@pytest.mark.parametrize("hostile", HOSTILE)
def test_crtsh_window_escapes_certificate_names_and_issuers(hostile):
    block = {"status": "ok", "data": {
        "certificate_count": 1, "first_seen": "2020-01-01T00:00:00", "last_seen": "2020-01-01T00:00:00",
        "issuers": [hostile], "names": ["example.com", hostile], "names_truncated": False}}
    out = render.source_window("crtsh", block)
    assert hostile not in out
    assert "<script" not in out and "<img src=x" not in out
    assert "&lt;" in out and balanced(out)


@pytest.mark.parametrize("hostile", HOSTILE)
def test_rdap_and_dns_windows_escape_values(hostile):
    rdap = {"status": "ok", "data": {"registrar": hostile, "registered": hostile, "expires": None, "last_changed": None,
                                      "statuses": [hostile], "nameservers": [hostile], "registry_url": hostile}}
    dns = {"status": "ok", "data": {"resolver": "dns.google", "rcode": "NOERROR", "A": [{"value": hostile, "ttl": 1}],
                                     "AAAA": [], "NS": [], "MX": [], "TXT": [{"value": hostile, "ttl": 1}]}}
    for key, block in (("rdap", rdap), ("dns", dns)):
        out = render.source_window(key, block)
        assert hostile not in out and "<script" not in out and "<img src=x" not in out
        assert balanced(out)


@pytest.mark.parametrize("hostile", HOSTILE)
def test_error_and_dialog_text_and_titles_are_escaped(hostile):
    block = {"status": "error", "data": None, "error": {"code": hostile, "message": hostile}}
    out = render.source_window("crtsh", block)
    assert hostile not in out and "<script" not in out and "<img src=x" not in out
    assert "does NOT mean there is no data" in out
    assert hostile not in theme.dialog("warn", hostile, hostile)
    assert hostile not in theme.window(hostile, "<p>ok</p>")


def test_raw_json_window_escapes_the_body():
    out = render.raw_json_window({"x": "<script>alert(1)</script>"})
    assert "<script" not in out and "&lt;script&gt;" in out and balanced(out)


def test_not_found_and_error_states_have_the_right_words():
    nf = render.source_window("rdap", {"status": "not_found", "data": None})
    assert "Not found" in nf and ".de or .io" in nf and "subdomains" in nf
    err = render.source_window("dns", {"status": "error", "data": None, "error": {"code": "timeout", "message": "slow"}})
    assert "Error (timeout)" in err and "the check could not be completed" in err


def test_status_is_never_conveyed_by_colour_alone():
    ok = render.source_window("rdap", {"status": "ok", "data": {"registrar": "R", "registered": "x", "expires": "y",
                                                                  "last_changed": "z", "statuses": [], "nameservers": [], "registry_url": "u"}})
    assert "OK: the source answered with data." in ok


def test_window_dialog_and_taskbar_are_balanced_and_decorations_are_hidden_from_screen_readers():
    for out in (theme.window("T", "<p>x</p>"), theme.dialog("error", "T", "m"), theme.taskbar("<img>", datetime(2026, 11, 5, 14, 5))):
        assert balanced(out)
    assert 'aria-hidden="true"' in theme.window("T", "x")
    assert "2:05 PM" in theme.taskbar("", datetime(2026, 11, 5, 14, 5))


def test_nothing_is_loaded_from_outside():
    css = theme.css_block()
    assert "http://" not in css and "https://" not in css and "@import" not in css and "url(" not in css
