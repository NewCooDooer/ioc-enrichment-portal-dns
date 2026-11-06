# Milestone log

Evidence for each milestone (commands, JSON, screenshots, pull requests). Updated as work lands.

## Milestone 0: design
- Status: done (merged via PR #1)
- Branch: `docs/design-md`
- Evidence: `design.md`, `docs/interview.md`; draft checked against the 8 required topics and project requirements in plan mode (2026-11-05)
- Pull request: #1 "Milestone 0: design.md for DNS-name IOC enrichment portal"

## Milestone 1: thinnest slice (Google DoH)
- Status: done (merged via PR #2)
- Branch: `feat/milestone-1`
- Plan: written in plan mode from `design.md` and approved before any code
- Source: Google Public DNS over HTTPS (keyless). Python 3.14.7, FastAPI 0.162.0, Streamlit 1.67.0, httpx 0.28.1

### Definition of done (design.md section 8)
| Check | Result |
|---|---|
| Backend returns the source's data for a valid name, per the contract | ✔ request 1 below |
| Invalid input returns a clear error, not a crash | ✔ requests 2 and 3 below; no stack trace |
| Frontend shows the result for a typed name | ✔ screenshot below |
| README explains install and run for both parts | ✔ `README.md` |
| No key or token in any commit | ✔ none needed; `git grep` for key/token/secret/password finds only a comment in `.env.example` and docs text |
| Merged into `main` through a PR | see PR link at the bottom |

Also checked: ports are configurable (a second backend ran on `BACKEND_PORT=8011`); with the backend stopped, the frontend client
reports "Could not reach the backend at http://127.0.0.1:8010 (ConnectError). Is it running?"; `python -m pytest` runs 25 validation tests offline.

### 1. Real IOC: request and JSON returned
```
$ curl -s -i http://127.0.0.1:8010/api/v1/domain/example.com
HTTP/1.1 200 OK
content-type: application/json
```
```json
{
  "ioc": { "type": "domain", "input": "example.com", "value": "example.com" },
  "sources": {
    "dns": {
      "status": "ok",
      "data": {
        "resolver": "dns.google",
        "rcode": "NOERROR",
        "A":    [{ "value": "104.20.23.154", "ttl": 300 }, { "value": "172.66.147.243", "ttl": 300 }],
        "AAAA": [{ "value": "2606:4700:10::6814:179a", "ttl": 203 }, { "value": "2606:4700:10::ac42:93f3", "ttl": 203 }],
        "NS":   [{ "value": "elliott.ns.cloudflare.com.", "ttl": 21600 }, { "value": "hera.ns.cloudflare.com.", "ttl": 21600 }],
        "MX":   [{ "value": "0 .", "ttl": 14 }],
        "TXT":  [{ "value": "v=spf1 -all", "ttl": 300 }, { "value": "_k2n1y4vw3qtb4skdx9e7dxt97qrmmq9", "ttl": 300 }]
      }
    }
  }
}
```
(Whitespace reformatted for reading; values are exactly what the backend returned.)

### 2. Frontend screenshot, same IOC
![Frontend showing example.com](screenshots/m1-frontend-example-com.jpg)

### 3. Invalid IOC: request and response
```
$ curl -s -i http://127.0.0.1:8010/api/v1/domain/10.0.0.1
HTTP/1.1 400 Bad Request
{"error":"not a valid DNS name: 10.0.0.1 (IP addresses are not accepted)","input":"10.0.0.1"}

$ curl -s -i "http://127.0.0.1:8010/api/v1/domain/not%20a%20name"
HTTP/1.1 400 Bad Request
{"error":"not a valid DNS name: not a name (URLs, ports, e-mail addresses and spaces are not accepted)","input":"not a name"}
```
Also verified: a nonexistent name returns 200 with `"dns": {"status": "not_found", "data": null}`; an unknown route returns 404 `{"error":"not found"}`.

### Bugs found and fixed while building
- `"type": "domain"` was missing from `ioc` because `response_model_exclude_unset` dropped a default value; the service now sets it explicitly.

### Pull request
#2 "Milestone 1: thinnest slice (Google DoH, FastAPI + Streamlit)": https://github.com/NewCooDooer/ioc-enrichment-portal-dns/pull/2

## Milestone 2: three sources, recorded tests
- Status: done (merged via PR #3)
- Branch: `feat/milestone-2` (plan written in plan mode and approved first)
- Sources: Google DoH, RDAP (rdap.org), crt.sh. All keyless; no key or token anywhere

### Definition of done (design.md section 8)
| Check | Result |
|---|---|
| One response holds a result from each of three real sources | ✔ evidence 1 |
| A failing source still returns the other two, with its error shown; all failing → 502 | ✔ evidence 3 + tests |
| Tests replay recorded responses and pass with the network off | ✔ evidence 2 (49 passed, also under an OS-level network-deny sandbox) |
| Tests cover a hit, an unknown name and a source error | ✔ `tests/test_api_contract.py` |
| No key in any recording or commit | ✔ fixtures hold only URL, status and body; grep for key/token/authorization/cookie finds nothing; e-mail-bearing certificate rows removed |
| design.md and README match the code | ✔ updated in this PR |
| Merged to main through a PR | see PR link at the bottom |

### Evidence 1: backend JSON for one IOC with all three sources
```
$ curl -s -m 70 http://127.0.0.1:8010/api/v1/domain/example.com      # HTTP 200, took about 16 s (crt.sh is slow)
```
```json
{
  "ioc": {
    "type": "domain",
    "input": "example.com",
    "value": "example.com"
  },
  "sources": {
    "dns": {
      "status": "ok",
      "data": {
        "resolver": "dns.google",
        "rcode": "NOERROR",
        "A": [
          { "value": "104.20.23.154", "ttl": 300 },
          { "value": "172.66.147.243", "ttl": 300 }
        ],
        "AAAA": [
          { "value": "2606:4700:10::ac42:93f3", "ttl": 245 },
          { "value": "2606:4700:10::6814:179a", "ttl": 245 }
        ],
        "NS": [
          { "value": "elliott.ns.cloudflare.com.", "ttl": 21600 },
          { "value": "hera.ns.cloudflare.com.", "ttl": 21600 }
        ],
        "MX": [
          { "value": "0 .", "ttl": 44 }
        ],
        "TXT": [
          { "value": "_k2n1y4vw3qtb4skdx9e7dxt97qrmmq9", "ttl": 300 },
          { "value": "v=spf1 -all", "ttl": 300 }
        ]
      }
    },
    "rdap": {
      "status": "ok",
      "data": {
        "registrar": "RESERVED-Internet Assigned Numbers Authority",
        "registered": "1995-08-14T04:00:00Z",
        "expires": "2027-08-13T04:00:00Z",
        "last_changed": "2026-08-14T08:01:43Z",
        "statuses": [
          "client delete prohibited",
          "client transfer prohibited",
          "client update prohibited"
        ],
        "nameservers": [
          "elliott.ns.cloudflare.com",
          "hera.ns.cloudflare.com"
        ],
        "registry_url": "https://rdap.verisign.com/com/v1/domain/example.com"
      }
    },
    "crtsh": {
      "status": "ok",
      "data": {
        "certificate_count": 45,
        "first_seen": "2010-09-02T16:36:49",
        "last_seen": "2026-09-26T22:49:11",
        "issuers": [
          "C=GB, O=Sectigo Limited, CN=Sectigo Public Server Authentication CA DV E36",
          "C=GB, O=Sectigo Limited, CN=Sectigo Public Server Authentication CA DV R36",
          "C=GB, O=Sectigo Limited, CN=Sectigo Public Server Authentication CA OV R36",
          "C=GB, ST=Cymru, O=AS207960 Cyfyngedig, OU=AS207960 Department of Random Numbers, CN=AS207960 Test CA",
          "C=GB, ST=Greater Manchester, L=Salford, O=Sectigo Limited, CN=Sectigo ECC Organization Validation Secure Server CA",
          "C=GB, ST=Greater Manchester, L=Salford, O=Sectigo Limited, CN=Sectigo RSA Domain Validation Secure Server CA",
          "C=US, O=\"CLOUDFLARE, INC.\", CN=Cloudflare TLS Issuing ECC CA 1",
          "C=US, O=\"CLOUDFLARE, INC.\", CN=Cloudflare TLS Issuing RSA CA 1",
          "C=US, O=\"thawte, Inc.\", CN=thawte SSL CA - G2",
          "C=US, O=DigiCert Inc, CN=DigiCert Global G2 TLS RSA SHA256 2020 CA1"
        ],
        "names": [
          "*.example.com",
          "AS207960 Test Intermediate - example.com",
          "dev.example.com",
          "example.com",
          "m.example.com",
          "m.testexample.com",
          "products.example.com",
          "subjectname@example.com",
          "support.example.com",
          "user@example.com",
          "www.example.com"
        ],
        "names_truncated": false
      }
    }
  }
}
```
(Whitespace reformatted; values are what the backend returned. crt.sh's `names` list shows the raw certificate names, which for example.com include a few sample e-mail style entries and test CA names.)

### Evidence 2: test output with the network off
```
$ sandbox-exec -p '(version 1)(allow default)(deny network*)' .venv/bin/python -m pytest -v
...
======================== 49 passed, 2 warnings in 0.26s ========================
```
- `sandbox-exec` with `(deny network*)` makes the operating system refuse every network connection; a direct test confirmed a real connect fails with `PermissionError: Operation not permitted`. Wi-Fi was not touched.
- The suite also enables `pytest-socket` (`--disable-socket`), and `tests/test_offline.py` asserts that a real connection raises `SocketBlockedError`.
- Breaking the code on purpose made the tests fail (mutation checks: skipping crt.sh's status check, and disabling the all-failed 502 rule), then I restored it.
- Test files: `test_api_contract.py` (hit, unknown, recorded crt.sh 502, simulated timeout / 429 / bad body, unexpected bug, all-fail 502, 400, 404), `test_sources.py`, `test_frontend_client.py`, `test_validation.py`, `test_offline.py`.

### Evidence 3: one source fails, and how I made it fail
How: started the backend with the crt.sh address pointed at a port where nothing is listening (the other two sources use their real defaults):
```
$ CRTSH_URL=http://127.0.0.1:9/ python -m backend
$ curl -s -i http://127.0.0.1:8010/api/v1/domain/example.com
HTTP/1.1 200 OK
server: uvicorn
content-length: 1124
content-type: application/json
```
```json
{
  "ioc": {
    "type": "domain",
    "input": "example.com",
    "value": "example.com"
  },
  "sources": {
    "dns": {
      "status": "ok",
      "data": {
        "resolver": "dns.google",
        "rcode": "NOERROR",
        "A": [
          { "value": "172.66.147.243", "ttl": 300 },
          { "value": "104.20.23.154", "ttl": 300 }
        ],
        "AAAA": [
          { "value": "2606:4700:10::ac42:93f3", "ttl": 204 },
          { "value": "2606:4700:10::6814:179a", "ttl": 204 }
        ],
        "NS": [
          { "value": "hera.ns.cloudflare.com.", "ttl": 19045 },
          { "value": "elliott.ns.cloudflare.com.", "ttl": 19045 }
        ],
        "MX": [
          { "value": "0 .", "ttl": 151 }
        ],
        "TXT": [
          { "value": "_k2n1y4vw3qtb4skdx9e7dxt97qrmmq9", "ttl": 274 },
          { "value": "v=spf1 -all", "ttl": 274 }
        ]
      }
    },
    "rdap": {
      "status": "ok",
      "data": {
        "registrar": "RESERVED-Internet Assigned Numbers Authority",
        "registered": "1995-08-14T04:00:00Z",
        "expires": "2027-08-13T04:00:00Z",
        "last_changed": "2026-08-14T08:01:43Z",
        "statuses": [
          "client delete prohibited",
          "client transfer prohibited",
          "client update prohibited"
        ],
        "nameservers": [
          "elliott.ns.cloudflare.com",
          "hera.ns.cloudflare.com"
        ],
        "registry_url": "https://rdap.verisign.com/com/v1/domain/example.com"
      }
    },
    "crtsh": {
      "status": "error",
      "data": null,
      "error": {
        "code": "upstream_error",
        "message": "could not reach crt.sh: ConnectError"
      }
    }
  }
}
```
(The `data` of `dns` and `rdap` is omitted here for length; it is the same as evidence 1.) The request still succeeds with HTTP 200; the failed source says `upstream_error` and why.
The real crt.sh also failed naturally: during testing it returned HTTP 502 for most calls, and one such 502 is recorded in `tests/fixtures/crtsh/error_502.json` and replayed by a test.

### Recording the fixtures
`python scripts/record_fixtures.py` saved real responses for a hit (`example.com`) and an unknown name (`this-does-not-exist-zzqq1234.com`) from each source, plus a real crt.sh 502.
crt.sh needed many retries (up to 9 attempts; one good answer took 54 s). Three of 85 certificate rows were dropped because their names contain e-mail addresses.

### Observations while building
- crt.sh succeeded about 1 time in 5 and sometimes took 16 to 54 s, so it got its own 25 s timeout (others 10 s); the end-to-end check afterwards showed that was too short, see the follow-up below.
- One lookup in about 16 had the DNS source fail with `RemoteProtocolError` (a dropped connection). It showed up correctly as a `dns` error block while the others returned, and did not repeat in 12 further lookups. No retry was added (retries are out of scope).
- Subdomains show RDAP `not_found` because RDAP only covers registered domains; decided to look the name up as typed.

### Pull request
#3 "Milestone 2: three sources and recorded offline tests": https://github.com/NewCooDooer/ioc-enrichment-portal-dns/pull/3

## Follow-up fix after the Milestone 2 end-to-end check
- Branch: `fix/crtsh-timeout-rdap-wording`
- Found by re-running everything on a fresh clone of `main` (2026-11-05): crt.sh good answers took 21, 30, 32 and 54 s, so the 25 s timeout threw away real answers; and RDAP answered "not found" for a real `.de` domain because rdap.org has no RDAP server for that TLD (also `.io`).
- Fixed: crt.sh timeout 25 s to 60 s; the frontend now waits 75 s (it must outlast the backend, enforced by a new test); the RDAP "not found" message in the UI, README, design.md and the RDAP source docstring now lists all three meanings (no such domain, subdomain, TLD not covered).
- Verified: 50 tests pass offline (also under the network-deny sandbox); the new test fails if the timeout is set back to 25 s; live runs against example.com, wikipedia.org and github.com (765 certificates, name list truncated at 50). crt.sh still fails most calls (HTTP 502, and sometimes 404), which the portal reports as an error for that source only.
- Pull request: #4 "Fix: crt.sh timeout too short, RDAP not-found wording": https://github.com/NewCooDooer/ioc-enrichment-portal-dns/pull/4

## Extra (optional): Windows 95 theme with Trojan Tim
- Branch: `feat/win95-theme` (planned in plan mode first; the owner chose the look and the mascot's personality)
- Scope: presentation only. No change to the backend, the API contract or `frontend/client.py`; no new dependencies.
- What it adds: a Windows 95 desktop (beveled windows, title bars, taskbar, error dialogs) and a mascot, Trojan Tim, who gives instructions and narrates results.
- Rules built in and tested (`tests/test_mascot.py`, `tests/test_theme.py`): Tim never gives a verdict (clean / safe / malicious / benign / trusted); a source that could not be checked is never described as "no data"; every source-supplied string is HTML-escaped (a crt.sh certificate name such as `<script>...` renders as text).
- Verified: 76 tests pass (26 new); four deliberate breaks (a verdict word, "no data" wording, no escaping in the tables, no escaping in the speech bubble) each made the matching tests fail, then were reverted; the page contacts only `localhost` (checked with the browser's resource list), its only image is an embedded data URI; keyboard Tab reaches the input and button with a visible dotted focus ring; the 375 px phone layout stacks Tim above his bubble.
- Evidence: `docs/screenshots/win95-1-idle.jpg` to `win95-6-mobile.jpg` (real lookups of example.com against the live services, including a real crt.sh failure).
- Status: done (merged via PR #5)
- Pull request: #5 "Frontend: Windows 95 theme with Trojan Tim": https://github.com/NewCooDooer/ioc-enrichment-portal-dns/pull/5

## Follow-up fix to the theme: icon font, Streamlit popup, Raw JSON layout
- Branch: `fix/theme-icons-raw-json`
- Found when the owner ran the app and sent screenshots: (1) a Streamlit developer popup ("Help agents write better apps ... Install the official Streamlit skills") appeared with garbled text, "auto_awesome" and "close" printed as words; (2) the Raw JSON panel showed the JSON flattened into one paragraph (I had only ever screenshotted that panel closed).
- Causes, reproduced in the browser first: (1) my theme CSS forced the Windows 95 font onto every `span`, including Streamlit's icon elements (`data-testid="stIconMaterial"`), so icon names rendered as text; the popup itself is Streamlit's own promo for app developers (`stSkillsNudge`), not part of this project; (2) Streamlit's markdown pass collapses newlines and spaces even inside `<pre>`.
- Fixed: the font rule now skips icon elements and the icon font is restored explicitly; the developer popup is hidden; the Raw JSON uses explicit `<br>` line breaks and `&nbsp;` indentation (every value still HTML-escaped).
- Verified: 78 tests pass (2 new); three deliberate breaks (icons overridden again, popup shown again, back to `<pre>`) each failed the matching test; in the live page an element with Streamlit's icon marker gets "Material Symbols Rounded" (a 16 px glyph, not a 12-letter word), an element with the popup marker is `display: none`, and normal text keeps the Windows 95 font; the opened Raw JSON panel shows indented lines (`docs/screenshots/win95-7-raw-json-open.jpg`).
- Not verified: Streamlit decided not to show the popup again after its first appearance on this machine, so I confirmed the hiding rule on a stand-in element carrying the same marker, not on the real popup.
- Pull request: #6 "Fix theme: icon font, Streamlit popup, raw JSON layout": https://github.com/NewCooDooer/ioc-enrichment-portal-dns/pull/6

## Follow-up fix: the web page listened on every network interface
- Branch: `fix/frontend-localhost-only`
- Found while writing the study guide: Streamlit printed a "Network URL" at startup. Measured before the fix: the page listened on `*:8510` and this Mac's own LAN address returned the full page (HTTP 200), so anyone on the same network could run lookups through it. The backend was already safe (`127.0.0.1`).
- Fixed: `[server] address = "127.0.0.1"` in `.streamlit/config.toml`; README and design.md updated; `tests/test_config.py` asserts both parts default to localhost.
- Verified after the fix: the page listens on 127.0.0.1:8510 only; localhost returns HTTP 200 and the Mac's LAN address is refused for both the page and the backend; 80 tests pass; re-binding to 0.0.0.0 makes the new test fail.
- Pull request: #7 "Fix: web page listens on localhost only": https://github.com/NewCooDooer/ioc-enrichment-portal-dns/pull/7

## Follow-up: readability cleanup (no behavior change)
- Branch: `refactor/plain-code`
- Why: the owner is a Python beginner and found some lines too dense to follow (for example the one-line `asyncio.gather(*(... for k in keys))` and the dictionary comprehensions). Chosen option: light cleanup only (not a rewrite).
- What changed: the densest lines in `service.py`, `validation.py`, `doh.py`, `rdap.py`, `crtsh.py`, `render.py` and `mascot.py` are now plain loops with beginner-friendly comments; `main.py` gained explanatory comments only. Same files, same functions, same API.
- Proof that nothing changed: before editing, the exact output of the app was recorded for 62 situations (real recordings, 25+ simulated source failures, bad input, 42 validation cases, parsers, rendering, Tim's text). After the cleanup the same script produced a byte-for-byte identical file. The recording script was itself checked to be repeatable (two runs identical). Also: 80 tests pass (also under the OS network-deny sandbox), Tim's picture data is identical to the version in git, and a live lookup against the real services still works.
- Pull request: _filled in after it is opened_

