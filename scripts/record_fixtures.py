"""Record real responses from the three sources into tests/fixtures/ (run by hand, never by the tests).

    python scripts/record_fixtures.py

Saves ONLY the request URL, status code, redirect target and body. No request or response headers are
saved, and no source here needs a key, so nothing secret can end up in a fixture.
crt.sh is flaky: it is retried until the wanted state (a 200 answer, or a real 502) is observed.
"""

import json
import sys
import time
from datetime import date
from pathlib import Path

import httpx

FIXTURES = Path(__file__).resolve().parent.parent / "tests" / "fixtures"
HIT = "example.com"
UNKNOWN = "this-does-not-exist-zzqq1234.com"
DOH_TYPES = {"A": 1, "NS": 2, "MX": 15, "TXT": 16, "AAAA": 28}
USER_AGENT = "ioc-enrichment-portal-dns/0.1 (training project; fixture recorder)"


def fetch(client: httpx.Client, url: str, params: dict | None = None) -> list[dict]:
    """GET without following redirects automatically, so every hop is recorded."""
    hops = []
    for _ in range(5):
        response = client.get(url, params=params, follow_redirects=False, timeout=60.0)
        hop = {"url": str(response.url), "status": response.status_code}
        if response.is_redirect:
            hop["location"] = str(response.next_request.url)
            hops.append(hop)
            url, params = hop["location"], None
            continue
        raw = response.text
        try:
            parsed = json.loads(raw)
            if len(raw) < 20000:
                hop["body_json"] = parsed
            else:
                hop["body_text"] = raw
        except ValueError:
            hop["body_text"] = raw
        hops.append(hop)
        return hops
    raise RuntimeError("too many redirects")


def scrub_emails(hop: dict) -> str | None:
    """Drop certificate rows whose names contain e-mail addresses: third-party personal data we don't need."""
    rows = _rows(hop)
    if not isinstance(rows, list) or not rows:
        return None
    kept = [r for r in rows if "@" not in r.get("name_value", "") and "@" not in r.get("common_name", "")]
    if len(kept) == len(rows):
        return None
    hop.pop("body_json", None)
    hop["body_text"] = json.dumps(kept, separators=(",", ":"))
    return (f"Real crt.sh response. {len(rows) - len(kept)} of {len(rows)} certificate rows removed because "
            "their names contain e-mail addresses (privacy). Nothing else changed.")


def save(source: str, case: str, exchanges: list[dict], note: str | None = None) -> None:
    path = FIXTURES / source / f"{case}.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    document = {"recorded": date.today().isoformat(), "exchanges": exchanges}
    if note:
        document["note"] = note
    path.write_text(json.dumps(document, indent=2, ensure_ascii=False) + "\n")
    print(f"saved {path.relative_to(FIXTURES.parent.parent)} ({path.stat().st_size} bytes)")


def record_doh(client: httpx.Client, case: str, name: str) -> None:
    exchanges = []
    for number in DOH_TYPES.values():
        exchanges += fetch(client, "https://dns.google/resolve", {"name": name, "type": number})
    save("doh", case, exchanges)


def record_rdap(client: httpx.Client, case: str, name: str) -> None:
    save("rdap", case, fetch(client, f"https://rdap.org/domain/{name}"))


def record_crtsh_until(client: httpx.Client, case: str, name: str, want, attempts: int = 25) -> bool:
    for attempt in range(1, attempts + 1):
        started = time.time()
        try:
            exchanges = fetch(client, "https://crt.sh/", {"q": name, "output": "json"})
        except httpx.HTTPError as exc:
            print(f"  crt.sh attempt {attempt}: {type(exc).__name__}")
            time.sleep(3)
            continue
        status = exchanges[-1]["status"]
        print(f"  crt.sh attempt {attempt}: HTTP {status} in {time.time() - started:.1f}s")
        if want(exchanges[-1]):
            save("crtsh", case, exchanges, note=scrub_emails(exchanges[-1]))
            return True
        time.sleep(3)
    print(f"  could not record crtsh/{case} after {attempts} attempts")
    return False


def main() -> int:
    ok = True
    with httpx.Client(headers={"User-Agent": USER_AGENT}) as client:
        print("DNS over HTTPS")
        record_doh(client, "hit", HIT)
        record_doh(client, "unknown", UNKNOWN)
        print("RDAP")
        record_rdap(client, "hit", HIT)
        time.sleep(2)
        record_rdap(client, "unknown", UNKNOWN)
        print("crt.sh (flaky: retrying until the wanted state appears)")
        ok &= record_crtsh_until(client, "error_502", HIT, lambda h: h["status"] == 502)
        ok &= record_crtsh_until(
            client, "hit", HIT, lambda h: h["status"] == 200 and isinstance(_rows(h), list) and len(_rows(h)) > 0
        )
        ok &= record_crtsh_until(
            client, "unknown", UNKNOWN, lambda h: h["status"] == 200 and _rows(h) == []
        )
    return 0 if ok else 1


def _rows(hop: dict):
    if "body_json" in hop:
        return hop["body_json"]
    try:
        return json.loads(hop.get("body_text", ""))
    except ValueError:
        return None


if __name__ == "__main__":
    sys.exit(main())
