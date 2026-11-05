"""Trojan Tim's content rules: facts only, never a verdict, and a failed check never sounds like "nothing there"."""

import re

import pytest
from client import Result

import mascot
from conftest import mount, mount_world

# Words that would be a verdict. Tim's own sentences must never contain them.
VERDICT_WORDS = re.compile(
    r"\b(clean|safe|safely|malicious|benign|trusted|trustworthy|harmless|legit|legitimate|virus-free|infected)\b", re.IGNORECASE
)


def said(lines: list[str]) -> str:
    return " ".join(lines)


def result_from(client, path: str) -> Result:
    response = client.get(path)
    return Result(response.status_code, response.json(), None if response.status_code == 200 else response.json().get("error"))


def test_every_fixed_message_is_free_of_verdict_words():
    texts = [
        mascot.narrate_idle(), mascot.narrate_working(),
        mascot.narrate(Result(None, None, "Could not reach the backend")),
        mascot.narrate(Result(400, {"error": "not a valid DNS name: x"}, "not a valid DNS name: x")),
        mascot.narrate(Result(502, {"error": "all sources failed"}, "all sources failed")),
        mascot.narrate(Result(500, None, "HTTP 500")),
    ]
    for lines in texts:
        assert not VERDICT_WORDS.search(said(lines)), lines


def test_hit_is_narrated_as_facts_with_the_sign_off(client, mock):
    mount_world(mock, "hit")
    lines = mascot.narrate(result_from(client, "/api/v1/domain/example.com"))
    text = said(lines)
    assert not VERDICT_WORDS.search(text)
    assert "example.com" in lines[0]
    assert "IPv4" in text and "IPv6" in text and "name servers" in text
    assert "registered 1995-08-14" in text and "RESERVED-Internet Assigned Numbers Authority" in text
    assert "certificates on record" in text
    assert lines[-1] == mascot.SIGN_OFF == "I only report facts. You decide what they mean."


def test_unknown_name_is_not_found_not_a_verdict(client, mock):
    mount_world(mock, "unknown")
    text = said(mascot.narrate(result_from(client, "/api/v1/domain/this-does-not-exist-zzqq1234.com")))
    assert not VERDICT_WORDS.search(text)
    assert "does not exist (NXDOMAIN)" in text
    assert "no registration record" in text and "no certificates on record" in text


def test_failed_source_is_never_described_as_no_data(client, mock):
    mount(mock, "doh", "hit")
    mount(mock, "rdap", "hit")
    mount(mock, "crtsh", "error_502")  # the real recorded crt.sh 502
    lines = mascot.narrate(result_from(client, "/api/v1/domain/example.com"))
    crt_line = next(line for line in lines if line.startswith("crt.sh"))
    assert "couldn't check" in crt_line and "not the same as finding nothing" in crt_line
    assert "no data" not in crt_line.lower() and "no certificates" not in crt_line
    assert not VERDICT_WORDS.search(said(lines))


def test_backend_down_and_invalid_input_and_all_failed():
    down = said(mascot.narrate(Result(None, None, "Could not reach the backend")))
    assert "can't reach my brain" in down and "python -m backend" in down
    bad = said(mascot.narrate(Result(400, {"error": "x"}, "not a valid DNS name: 10.0.0.1 (IP addresses are not accepted)")))
    assert "10.0.0.1" in bad and "no IP addresses" in bad
    failed = said(mascot.narrate(Result(502, {"error": "all sources failed"}, "all sources failed")))
    assert "nothing to report" in failed and "tells us nothing about the domain" in failed


@pytest.mark.parametrize("hostile", ["<script>alert(1)</script>", '"><img src=x onerror=alert(1)>', "<b>bold</b>"])
def test_speech_bubble_escapes_everything(hostile):
    out = mascot.popup([f"RDAP: registered through {hostile}"])
    assert hostile not in out
    assert "<script" not in out and "<img src=x" not in out
    assert "&lt;" in out


def test_tim_picture_is_self_contained():
    uri = mascot.tim_data_uri()
    assert uri.startswith("data:image/svg+xml;base64,")
    img = mascot.tim_img()
    assert 'alt="Trojan Tim' in img and "http" not in img
