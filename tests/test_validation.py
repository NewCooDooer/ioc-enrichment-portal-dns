import pytest

from backend.app.validation import InvalidDomain, normalize_domain


@pytest.mark.parametrize(
    "raw, expected",
    [
        ("example.com", "example.com"),
        ("Example.COM", "example.com"),
        ("  example.com. ", "example.com"),
        ("login.example.com", "login.example.com"),
        ("_dmarc.example.com", "_dmarc.example.com"),
        ("bücher.de", "xn--bcher-kva.de"),
        ("xn--bcher-kva.de", "xn--bcher-kva.de"),
    ],
)
def test_valid_names_are_normalized(raw, expected):
    assert normalize_domain(raw) == expected


@pytest.mark.parametrize(
    "raw",
    [
        "",
        "   ",
        "10.0.0.1",
        "8.8.8.8",
        "2001:db8::1",
        "localhost",
        "https://example.com",
        "example.com/path",
        "user@example.com",
        "example.com:8080",
        "not a name",
        "-bad.example.com",
        "bad-.example.com",
        "exa mple.com",
        "a..b.com",
        "example.123",
        ("a" * 64) + ".com",
        ".".join(["a" * 60] * 5) + ".com",
    ],
)
def test_invalid_names_are_rejected(raw):
    with pytest.raises(InvalidDomain):
        normalize_domain(raw)
