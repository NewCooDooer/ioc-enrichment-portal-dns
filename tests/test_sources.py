"""Unit tests for the parsing code of each source, using recorded bodies and hand-made edge cases."""

from backend.app.sources import crtsh, rdap
from conftest import load_exchanges


def test_rdap_parse_recorded_hit():
    final = load_exchanges("rdap", "hit")[-1]
    data = rdap.parse(final["body_json"], final["url"])
    assert data["registrar"] == "RESERVED-Internet Assigned Numbers Authority"
    assert data["registered"] == "1995-08-14T04:00:00Z"
    assert data["expires"] and data["last_changed"]
    assert "client delete prohibited" in data["statuses"]
    assert data["registry_url"].endswith("/domain/example.com")


def test_rdap_parse_tolerates_missing_fields():
    data = rdap.parse({}, "https://example.invalid/x")
    assert data == {
        "registrar": None, "registered": None, "expires": None, "last_changed": None,
        "statuses": [], "nameservers": [], "registry_url": "https://example.invalid/x",
    }


def _row(serial, names, not_before="2026-01-01T00:00:00", issuer="CN=Test CA"):
    return {"serial_number": serial, "issuer_name": issuer, "not_before": not_before, "name_value": names}


def test_crtsh_summarize_counts_each_serial_once():
    rows = [_row("aa", "a.example.com\nb.example.com"), _row("aa", "a.example.com"), _row("bb", "c.example.com")]
    summary = crtsh.summarize(rows)
    assert summary["certificate_count"] == 2
    assert summary["names"] == ["a.example.com", "b.example.com", "c.example.com"]
    assert summary["names_truncated"] is False


def test_crtsh_summarize_dates_and_issuers():
    rows = [
        _row("1", "x.com", "2026-03-01T00:00:00", "CN=B CA"),
        _row("2", "x.com", "2025-01-01T00:00:00", "CN=A CA"),
    ]
    summary = crtsh.summarize(rows)
    assert summary["first_seen"] == "2025-01-01T00:00:00"
    assert summary["last_seen"] == "2026-03-01T00:00:00"
    assert summary["issuers"] == ["CN=A CA", "CN=B CA"]


def test_crtsh_summarize_caps_names_and_issuers():
    rows = [_row(str(i), f"n{i:03}.example.com", issuer=f"CN=CA {i:02}") for i in range(80)]
    summary = crtsh.summarize(rows)
    assert len(summary["names"]) == 50 and summary["names_truncated"] is True
    assert len(summary["issuers"]) == 10
