# IOC Enrichment Portal (DNS names): design

Status: **ready for review (Milestone 0)** · Last updated: 2026-11-05 · Owner: Evan Murphy
Read this file before changing the API or adding a feature (see `CLAUDE.md`).

## 1. Goal

A SOC analyst types a **DNS name** (e.g. `example.com`, `login.example.com`) into a web page and sees
enrichment from three real, keyless sources in one place:

| Question | Source |
|---|---|
| What does it resolve to right now? | DNS over HTTPS (Google Public DNS) |
| Who registered it, when, with which registrar? | RDAP via rdap.org |
| Which TLS certificates were ever issued for it? | crt.sh (Certificate Transparency) |

The same backend is called by other programs later this week (a classmate's caching work, an MCP server,
the Sysmon portal), so the **API contract is the product**; the web page is one client of it.

### Out of scope for this version (do not add; reject in review)

- Database, accounts/login, caching, retries/backoff, request queues (caching comes in *Reading Unfamiliar Code*)
- Privacy guard that blocks private/internal values (comes in *Secure Coding with AI*; the rule is documented in section 8)
- Optimization, bulk/batch lookups, scheduling, persistence of lookup history
- Reputation verdicts (no source here says "malicious"; the UI must not imply one)
- Containers (we run without Docker; Docker is not installed on the dev machine)
- Uploading anything to VirusTotal (VirusTotal is not used at all)

## 2. Architecture

```
 Browser ──► Streamlit frontend (port 8510) ──HTTP/JSON──► FastAPI backend (port 8010) ──► DoH / RDAP / crt.sh
              never calls a source                         validates, fans out in parallel,
                                                           normalizes, merges
```

- **Two separate Python apps** in one repo: `backend/` and `frontend/`. Other programs call the backend directly.
- The frontend talks **only** to the backend, using `BACKEND_URL` (default `http://127.0.0.1:8010`).
- The backend queries the three sources **concurrently** (`asyncio` + `httpx`), each with its own timeout
  and its own error handling, then returns one merged JSON object.
- Ports are configurable: `BACKEND_PORT` (default 8010), `FRONTEND_PORT` (default 8510). Defaults avoid the
  common 8000/8501 so two portals can share one laptop in the Sysmon project.

Planned layout: `backend/app/` (main, config, validation, models, `sources/`), `frontend/app.py`, `tests/` (with `fixtures/`), `scripts/record_fixtures.py`, `docs/`, `.env.example`. Update this file if it changes.

## 3. Stack and decisions (each with its reason)

| Decision | Choice | Reason / what would change it |
|---|---|---|
| Backend framework | **FastAPI** + uvicorn | Typed response models make the contract executable and auto-generate OpenAPI docs; native async lets three slow sources run in parallel. Would change if the async code proved hard to debug. |
| HTTP client | **httpx** (async) | One client for all sources; `respx` mocks it cleanly in tests. Follows redirects (needed for rdap.org, `follow_redirects=True`). |
| Frontend | **Streamlit** | Pure Python, minimal code, calls the backend with `httpx`/`requests`. Would change if we needed custom layout. |
| Validation | **stdlib** (`re`, `str.encode("idna")`) | No extra dependency. Caveat: Python's built-in codec is IDNA 2003 and may reject some valid names; M1 checks this, and if it fails we switch to the `idna` package. |
| Repository visibility | **Public** GitHub repo | The course requirement says private, but the instructor must be able to evaluate the work. Safe because there are no keys, and fixtures hold only public data. Deviation approved by the owner. |
| Tests | **pytest + respx + pytest-socket** | Replay fixtures through the real parsing code; `pytest-socket` blocks all sockets so "network off" is *enforced*, not assumed. |
| Fixtures | **Saved JSON files** in `tests/fixtures/` loaded by tests | Readable, reviewable diffs, no hidden headers (a recorder script saves status and body only), easy for a classmate to read. Chosen over VCR cassettes, which can capture headers/keys. |
| Config | Environment variables, optional `.env` (python-dotenv) | Keys (none yet) never touch code. |
| Containers | **None** | Satisfies "at most two"; fewer moving parts. |
| Python | 3.11+ (dev machine: 3.14.7) | Verify dependency wheels on 3.14 at milestone 1; pin the minor version in README. |
| Dependency pinning | `requirements.txt` (runtime) + `requirements-dev.txt` | Simple for a classmate to install. |

Open (not decided yet): whether to add Cloudflare DoH as a fallback for Google DoH. Default: **no**, single resolver in v1.

## 4. Input rules

The path parameter is normalized, then validated; failure returns **400** (never a crash, never a source call).

1. Trim whitespace, drop one trailing dot, lowercase.
2. Reject: empty, containing `/ : @ ? # ` or spaces (URLs, emails, ports), IP addresses (v4/v6),
   a single label (`localhost`), total length > 253, any label empty or > 63, or label starting/ending with `-`.
3. Non-ASCII labels are converted to punycode (`bücher.de` → `xn--bcher-kva.de`); the response echoes both
   the original input and the normalized value.
4. Characters outside `a-z 0-9 - _` after punycode are rejected (underscore allowed for names such as `_dmarc.example.com`).

## 5. API contract (version 1)

Base path `/api/v1`. All responses are JSON. Unknown routes return FastAPI's default 404.

### `GET /api/v1/domain/{name}`

**200 OK**: input was valid and at least one source answered (ok or not_found). Example for `example.com`
(abridged; values from real lookups on 2026-11-05):

```json
{
  "ioc": { "type": "domain", "input": "Example.com", "value": "example.com" },
  "sources": {
    "dns": {
      "status": "ok",
      "data": {
        "resolver": "dns.google",
        "rcode": "NOERROR",
        "A":    [{ "value": "104.20.23.154", "ttl": 300 }, { "value": "172.66.147.243", "ttl": 300 }],
        "AAAA": [], "NS": [], "MX": [], "TXT": []
      }
    },
    "rdap": {
      "status": "ok",
      "data": {
        "registrar": "RESERVED-Internet Assigned Numbers Authority",
        "registered": "1995-08-14T04:00:00Z",
        "expires": "2027-08-13T04:00:00Z",
        "last_changed": "2026-08-14T08:01:43Z",
        "statuses": ["client delete prohibited", "client transfer prohibited", "client update prohibited"],
        "nameservers": ["elliott.ns.cloudflare.com", "hera.ns.cloudflare.com"],
        "registry_url": "https://rdap.verisign.com/com/v1/domain/example.com"
      }
    },
    "crtsh": {
      "status": "error",
      "data": null,
      "error": { "code": "upstream_error", "message": "crt.sh returned HTTP 502" }
    }
  }
}
```

(The example shows crt.sh failing because it really did on 2026-11-05; final example values are re-recorded in Milestone 2.)

**Per-source block**, identical shape for every source:

| Field | Meaning |
|---|---|
| `status` | `"ok"` (source answered with data), `"not_found"` (source answered: nothing known about this name), `"error"` (we could not get an answer) |
| `data` | Object when `ok`, otherwise `null` |
| `error` | Present only when `status` is `"error"`: `{ "code": ..., "message": ... }` |

`error.code` is one of: `timeout`, `rate_limited` (HTTP 429), `upstream_error` (5xx / other HTTP failure),
`invalid_response` (unparseable body), `missing_key` (reserved for future keyed sources).
**How a caller tells "no data" from "source failed": `not_found` is an answer; `error` is not.**

Source-specific meaning of `not_found`: DoH → `rcode` NXDOMAIN; RDAP → HTTP 404; crt.sh → empty list.
A name that exists but has no records of a type is `ok` with empty arrays.

crt.sh `data` (summary, not raw rows): `certificate_count`, `first_seen`, `last_seen`, `issuers` (distinct, max 10),
`names` (distinct SAN names, capped at 50, with `names_truncated` boolean).

### `GET /api/v1/health`
`200 {"status": "ok"}`. No source calls.

### Errors

One error format everywhere: `{ "error": "<problem>", "input": "<bad input if any>" }`.

| Status | When | Body |
|---|---|---|
| 400 | Invalid DNS name | `{ "error": "not a valid DNS name: 10.0.0.1 (IP addresses are not accepted)", "input": "10.0.0.1" }` |
| 502 | **All three** sources returned `error` | `{ "error": "all sources failed", "input": "...", "sources": { …per-source blocks… } }` |
| 500 | Unexpected bug | `{ "error": "internal error" }` (details logged, not returned) |

429 is not returned by this backend in v1 (no rate limiting here); source 429s appear as `rate_limited` in the source block.
A single failing source never changes the status code: the other sources still return (Milestone 2 requirement).

Breaking changes go to `/api/v2/`; v1 keeps working.

## 6. Data sources (checked on the providers' own pages, 2026-11-05)

| Source | Key | Limit | Terms / notes |
|---|---|---|---|
| **Google Public DNS, DoH JSON API** `https://dns.google/resolve?name=…&type=…` ([docs](https://developers.google.com/speed/public-dns/docs/doh/json)) | No | The docs page states **no numeric limit**; on excess it returns HTTP 429 and clients must honor `Retry-After`. (Course material cites 1,500 queries/s per IP; I did not find that figure on the page.) | Docs page has no terms. The [privacy page](https://developers.google.com/speed/public-dns/privacy) says queries (your IP + domain) sit in temporary logs for 24–48 h and a sampled permanent log keeps the domain name with a coarse location. Google says it does not use them for ad targeting. **Every name we look up is disclosed to Google.** |
| **RDAP via rdap.org** `https://rdap.org/domain/{name}` ([about](https://about.rdap.org/)) | No | **10 requests per 10 s** (Cloudflare), then 429. Higher limits only for supporters. | Redirects (302) to the registry's own RDAP server → client must follow redirects. 404 = no authoritative service known or no such domain. 403 = blocked for abuse. No formal ToS; only aggregated stats collected. Heavy users are told to use the IANA bootstrap files directly. |
| **crt.sh** `https://crt.sh/?q={name}&output=json` | No | **None published.** Community reports suggest ≈5 requests/minute/IP (unverified, vendor blogs). Real observation: **HTTP 502 on 2026-11-05** (two attempts). | No official terms or API documentation found (page shows only "© Sectigo Limited 2015-2026"). Operated by Sectigo as a public service. Treat as fair use: one call per user request, no bulk. **Open item: re-check before Milestone 2 merge.** |

Observed 2026-11-05: DoH `example.com` → 2 A records; RDAP → 302 to `rdap.verisign.com`, then 200 (nonexistent `.com` → 404); crt.sh → 502.
"None published" ≠ unlimited: tests never call these services (section 9).

## 7. Where the work is split: frontend ↔ backend

- Frontend (Streamlit): one text box, one button. Calls `GET {BACKEND_URL}/api/v1/domain/{name}`.
  Renders one card per source (ok / not found / error with the message), and a clear message for 400/502.
  It labels what each source says and **never shows a "clean" or "safe" badge**: no source here gives a verdict.
- Backend: owns validation, all external calls, timeouts (10 s per source, 15 s overall), normalization and merging.
- Backend CORS: not enabled (Streamlit calls server-side). Revisit if a browser-based client appears.

## 8. Secrets and values that must never leave the machine

- **Keys:** none required in v1 (all three sources are keyless). If a keyed source is added, its key lives in `.env`
  (gitignored) or the environment, documented in `.env.example` with empty values. Keys never appear in code,
  logs, fixtures or commits. `scripts/record_fixtures.py` saves only status + body, no request headers or query-string secrets.
- **Never send to any outside service** (documented now, enforced in *Secure Coding with AI*):
  RFC 1918 addresses (`10/8`, `172.16/12`, `192.168/16`), internal host names and domains
  (`*.local`, `*.internal`, `*.corp`, `*.lan`, `*.home.arpa`, single-label names, the company's own domains),
  and hashes of internal files. A lookup tells Google/Verisign/Sectigo that the name exists and is under investigation,
  and crt.sh and DNS logs are not private.
- Until the guard exists, the README states: **do not enter internal names.**

## 9. Tests: recorded, offline

- `scripts/record_fixtures.py` calls each real source once and saves `status` + `body` into
  `tests/fixtures/<source>/<case>.json` (one-time, manual, never run by tests).
- Tests use **respx** to serve these fixtures to the real client/parsing code, and `pytest-socket` (`--disable-socket`)
  so any real network attempt fails the test. Proof: run `pytest` with Wi-Fi off.
- Cases per source: **hit** (`example.com`), **unknown** (a nonexistent name), **error** (recorded 502 from crt.sh;
  429 and timeout are simulated by respx from the recorded shape, and labeled as simulated).
- Plus: validation unit tests (good/bad inputs), contract tests on the merged response, and the 502 "all failed" case.
- Frontend: the function that calls the backend is unit-tested with respx (200, 400, 502, backend down); the Streamlit page itself is checked by hand with a screenshot.
- Fixtures are reviewed before commit: grep for `key`, `token`, `Authorization` (none expected).

## 10. Milestones

Progress and evidence for each milestone are logged in `docs/milestones.md` (commands run, JSON, screenshots, PR numbers).

### Milestone 0: design (this document)
Done when: `design.md` covers the eight required topics; interview notes in `docs/interview.md`; `.gitignore`, `.gitattributes`,
README exist; merged to `main` through a pull request.

### Milestone 1: thinnest slice (one source: Google DoH)
Done when:
1. `GET /api/v1/domain/example.com` returns `ioc` + a `dns` block per the contract (the other two sources are omitted from `sources` in M1; contract adds them in M2 without breaking field names).
2. `GET /api/v1/domain/10.0.0.1` and `/api/v1/domain/not%20a%20name` return 400 with the contract's error body; no stack trace.
3. Streamlit page shows the DNS result for a name the user types, via the backend only.
4. README explains install and run for both parts, including `BACKEND_PORT` / `FRONTEND_PORT` / `BACKEND_URL`.
5. `git log -p` and `git grep` show no key/token (none exist yet).
6. Merged to `main` through a pull request; evidence in `docs/milestones.md`.

### Milestone 2: three sources, recorded tests
Done when:
1. One response holds `dns`, `rdap` and `crtsh` blocks for a real name.
2. With any one source failing (e.g. crt.sh 502 or a forced timeout) the other two still return and the failed block shows `status: "error"` plus code and message; all three failing returns 502.
3. Tests replay recorded responses and pass with the network off (`pytest --disable-socket`, and with Wi-Fi off).
4. Tests cover a hit, an unknown name, and a source error.
5. No key in any recording or commit.
6. `design.md` and README match the code (the layout and the examples re-checked).
7. Merged to `main` through a pull request; evidence in `docs/milestones.md`.

## 11. Open questions (not decided yet)

- Cloudflare DoH as fallback resolver (default: no).
- Which record types DoH should query beyond A/AAAA/NS/MX/TXT (default: those five, in parallel).
- crt.sh terms and effective rate limit: re-check at M2.
- Whether Python 3.14 wheels exist for all pinned dependencies (verify in M1; fall back to 3.12/3.13 if not).
