# IOC Enrichment Portal (DNS names): design

Status: Milestone 0 · Last updated: 2026-11-05 · Owner: Evan Murphy · Read this before changing the API (see `CLAUDE.md`).

## 1. Goal and scope

A SOC analyst types a **DNS name** into a web page and sees enrichment from three real, keyless sources:

| Question | Source |
|---|---|
| What does it resolve to? | Google Public DNS over HTTPS |
| Who registered it, and when? | RDAP via rdap.org |
| Which TLS certificates were issued for it? | crt.sh (Certificate Transparency) |

Other programs (a classmate's caching work, an MCP server, the Sysmon portal) call the same backend later this
week, so the **API contract is the product** and the web page is one client of it.

**Out of scope for this version** (reject in review): database, accounts, caching (comes in *Reading Unfamiliar Code*),
retries, bulk lookups, lookup history, optimization, containers, the privacy guard (comes in *Secure Coding with AI*;
the rule is in section 7), reputation verdicts (no source here says "malicious"; the UI must never show "clean" or "safe"),
and VirusTotal (not used; never upload files to it).

## 2. Architecture: backend and frontend

```
Browser → Streamlit frontend (:8510) ──HTTP/JSON──► FastAPI backend (:8010) ──► Google DoH · RDAP · crt.sh
```

- Two separate Python apps in `backend/` and `frontend/`. The frontend calls **only** the backend (`BACKEND_URL`,
  default `http://127.0.0.1:8010`) and never a source.
- The backend validates the input, queries the three sources **concurrently** (`asyncio` + `httpx`, 10 s timeout each),
  and returns one merged JSON object. Source errors never crash it.
- Frontend: one text box and button; one card per source (ok / not found / error + message); clear messages for 400/502.
- Ports are configurable (`BACKEND_PORT`, `FRONTEND_PORT`). Defaults avoid 8000/8501 so two portals can share a laptop.

## 3. Stack and decisions (with reasons)

| Decision | Choice | Reason / what would change it |
|---|---|---|
| Backend | **FastAPI** + uvicorn | Async runs three slow sources in parallel; typed models make the contract executable. Change if async proves hard to debug. |
| HTTP client | **httpx** | One client for all sources; follows redirects (rdap.org needs it); `respx` mocks it. |
| Frontend | **Streamlit** | Pure Python, minimal code for a one-box page. Change if we need a custom layout. |
| Validation | stdlib `re` + `str.encode("idna")` | No extra dependency. Built-in codec is IDNA 2003 and may reject some valid names; M1 tests `bücher.de` fine. Switch to the `idna` package if a real name fails. |
| Tests | **pytest + respx + pytest-socket** | Replay fixtures through the real parsing code; pytest-socket makes any real network call fail. |
| Fixtures | Saved JSON in `tests/fixtures/` | Readable, reviewable, no hidden headers that could hold a key. Chosen over vcrpy cassettes. |
| Config | Environment variables, optional `.env` | Secrets never in code. |
| Containers | None | Allowed (max two); Docker is not installed; fewer moving parts. |
| Python | 3.11+ (dev: 3.14.7) | Wheels for all dependencies verified on 3.14 in M1; versions pinned in `requirements.txt`. |
| Repo visibility | **Public** | Course says private, but the instructor must evaluate it; no keys, fixtures hold only public data. |

## 4. API contract (version 1)

Base path `/api/v1`, JSON everywhere. Breaking changes go to `/api/v2/`; v1 keeps working.

### Input rules
Trim, drop one trailing dot, lowercase. Reject (400): empty, `/ : @ ? #` or spaces, IP addresses, single labels
(`localhost`), over 253 characters, labels empty/over 63/starting or ending with `-`. Non-ASCII becomes punycode
(`bücher.de` → `xn--bcher-kva.de`); the response echoes both input and normalized value.

### `GET /api/v1/domain/{name}` → 200
Example for `example.com`, abridged (real values from 2026-11-05; crt.sh really returned 502):

```json
{
  "ioc": { "type": "domain", "input": "Example.com", "value": "example.com" },
  "sources": {
    "dns":   { "status": "ok", "data": { "resolver": "dns.google", "rcode": "NOERROR",
               "A": [{ "value": "104.20.23.154", "ttl": 300 }], "AAAA": [], "NS": [], "MX": [], "TXT": [] } },
    "rdap":  { "status": "ok", "data": { "registrar": "RESERVED-Internet Assigned Numbers Authority",
               "registered": "1995-08-14T04:00:00Z", "expires": "2027-08-13T04:00:00Z",
               "nameservers": ["elliott.ns.cloudflare.com", "hera.ns.cloudflare.com"],
               "registry_url": "https://rdap.verisign.com/com/v1/domain/example.com" } },
    "crtsh": { "status": "error", "data": null,
               "error": { "code": "upstream_error", "message": "crt.sh returned HTTP 502" } }
  }
}
```

**Every source block** has `status`, `data` and (only on error) `error`:
`ok` = answered with data; `not_found` = answered "nothing known" (DoH NXDOMAIN, RDAP 404, crt.sh empty list);
`error` = no answer. `error.code` is `timeout`, `rate_limited` (429), `upstream_error` (5xx), `invalid_response`
or `missing_key` (reserved). **`not_found` is an answer; `error` is not**, so callers can tell "no data" from "failed".
crt.sh `data` is a summary: `certificate_count`, `first_seen`, `last_seen`, up to 10 `issuers`, up to 50 `names`
(`names_truncated`). Milestone 1 returns only `dns`; `rdap` and `crtsh` are added in Milestone 2 without renaming fields.

### Other endpoints and errors
`GET /api/v1/health` → `200 {"status":"ok"}`. One error format everywhere: `{"error": "...", "input": "..."}`.

| Status | When | Example body |
|---|---|---|
| 400 | Invalid name | `{"error": "not a valid DNS name: 10.0.0.1 (IP addresses are not accepted)", "input": "10.0.0.1"}` |
| 502 | All sources errored | `{"error": "all sources failed", "input": "...", "sources": {…}}` |
| 500 | Unexpected bug | `{"error": "internal error"}` (details logged only) |

One failing source never changes the status code; the others still return. This backend returns no 429 in v1.
Unknown routes return 404 `{"error": "not found"}` in the same format. The path parameter accepts slashes so a pasted URL gets a 400, not a 404.

## 5. Data sources (provider pages, checked 2026-11-05)

| Source | Key | Limit | Terms / notes |
|---|---|---|---|
| **Google Public DNS JSON** `https://dns.google/resolve` ([docs](https://developers.google.com/speed/public-dns/docs/doh/json)) | No | Default **1500 queries/s per client IP** (IPv4 or IPv6 /64), short bursts allowed ([ISP docs](https://developers.google.com/speed/public-dns/docs/isp)); [troubleshooting page](https://developers.google.com/speed/public-dns/docs/troubleshooting) says **1000**. Neither mentions DoH specifically; on excess expect 429 + `Retry-After`. | Free, **no SLA**. [Privacy page](https://developers.google.com/speed/public-dns/privacy): IP + queried domain in temporary logs 24–48 h; sampled permanent log keeps the domain and coarse location. **Every name we look up is disclosed to Google.** |
| **RDAP** `https://rdap.org/domain/{name}` ([about](https://about.rdap.org/)) | No | **10 requests per 10 s**, then 429. | 302 redirect to the registry (client must follow); 404 = unknown; 403 = blocked for abuse. No formal ToS. |
| **crt.sh** `https://crt.sh/?q={name}&output=json` | No | None published; ~5/min reported by third parties (unverified). | No official terms found (run by Sectigo). Observed **HTTP 502 on 2026-11-05**. One call per lookup. Re-check in M2. |

"None published" does not mean unlimited; tests never call these services.

## 6. Tests: recorded, offline

- `scripts/record_fixtures.py` calls each real source once and saves **status + body only** to `tests/fixtures/<source>/<case>.json`.
- Tests serve those files with **respx** to the real parsing code; **pytest-socket** fails any real network call.
  Proof: run `pytest` with Wi-Fi off.
- Per source: a **hit** (`example.com`), an **unknown** name, and an **error** (recorded crt.sh 502; 429 and timeout
  are simulated from recorded shapes and labeled as such). Also: validation, merged-contract and all-failed (502) tests.
- Frontend: its backend-calling function is unit-tested with respx; the page itself is checked by hand with a screenshot.
- Before committing, grep fixtures for `key`, `token`, `Authorization`.

## 7. Secrets and values that must never leave the machine

- **Keys:** none in v1 (all sources keyless). Any future key lives in `.env` (gitignored) or the environment, with
  empty placeholders in `.env.example`; never in code, logs, fixtures or commits.
- **Never send to an outside service:** RFC 1918 addresses (10/8, 172.16/12, 192.168/16), internal host names and
  domains (`*.local`, `*.internal`, `*.corp`, `*.lan`, `*.home.arpa`, single-label names, company domains), hashes of
  internal files. A lookup reveals that the value exists and is being investigated. Enforced in code in *Secure Coding
  with AI*; until then the README says **do not enter internal names.**

## 8. Milestones (progress and evidence logged in `docs/milestones.md`)

**Milestone 0: design.** Done when this file covers the eight required topics, interview notes exist in `docs/interview.md`,
and it is merged to `main` through a pull request. ✔ PR #1.

**Milestone 1: thinnest slice (Google DoH only).** Evidence in `docs/milestones.md`. Done when:
1. `GET /api/v1/domain/example.com` returns `ioc` + `dns` as in the contract.
2. `/api/v1/domain/10.0.0.1` and `/api/v1/domain/not%20a%20name` return 400 with the error body, no stack trace.
3. The Streamlit page shows the result for a typed name, via the backend only.
4. README explains install and run for both parts, including `BACKEND_PORT`, `FRONTEND_PORT`, `BACKEND_URL`.
5. `git grep` shows no key or token in any commit.
6. Merged to `main` through a pull request.

**Milestone 2: three sources, recorded tests.** Done when:
1. One response holds `dns`, `rdap` and `crtsh` results for a real name.
2. With any one source failing, the other two still return and the failed block shows its error; all three failing returns 502.
3. Tests replay recordings and pass with the network off, covering a hit, an unknown name and a source error.
4. No key in any recording or commit.
5. `design.md` and README match the code.
6. Merged to `main` through a pull request.

## 9. Open questions

Cloudflare DoH as a fallback (default no) · record types beyond A/AAAA/NS/MX/TXT (default no) · crt.sh terms and real limit
(re-check in M2).
