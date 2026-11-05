# IOC Enrichment Portal: DNS names

A SOC lookup tool: enter a DNS name and see enrichment from real, keyless public sources in one place.
Python only, with a **FastAPI backend** and a separate **Streamlit frontend** that talks only to the backend.

**Status: Milestone 1 (thinnest slice).** One source works end to end: Google Public DNS over HTTPS
(A, AAAA, NS, MX, TXT records). RDAP and crt.sh arrive in Milestone 2.
Plan, API contract and decisions: [`design.md`](design.md). Progress and evidence: [`docs/milestones.md`](docs/milestones.md).

> **Do not enter internal or private names** (`*.corp`, `*.local`, your company's own domains).
> Lookups go to outside services (Google). A privacy guard comes in a later milestone.
> None of these sources gives a verdict: they report facts, and you decide what they mean.

## Install

Requires Python 3.11+ (developed on 3.14). No Docker, no API keys.

```bash
git clone https://github.com/NewCooDooer/ioc-enrichment-portal-dns.git
cd ioc-enrichment-portal-dns
python3 -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
pip install -r requirements-dev.txt
```

## Run

Start the backend (terminal 1):

```bash
python -m backend
```

Start the frontend (terminal 2):

```bash
streamlit run frontend/app.py --server.port "${FRONTEND_PORT:-8510}"
```

Open http://localhost:8510 and type a name such as `example.com`. The API itself is at http://127.0.0.1:8010
(interactive docs at `/docs`).

### Configuration (environment variables or a `.env` file; see `.env.example`)

| Variable | Default | Used by | Meaning |
|---|---|---|---|
| `BACKEND_HOST` | `127.0.0.1` | backend | address to listen on |
| `BACKEND_PORT` | `8010` | backend | port to listen on |
| `FRONTEND_PORT` | `8510` | frontend (`--server.port`) | port for the web page |
| `BACKEND_URL` | `http://127.0.0.1:8010` | frontend | where the frontend finds the backend |

Two portals on one laptop: give each its own ports, e.g. `BACKEND_PORT=8011 python -m backend` and
`BACKEND_URL=http://127.0.0.1:8011 streamlit run frontend/app.py --server.port 8511`.

## Try the API

```bash
curl -s http://127.0.0.1:8010/api/v1/domain/example.com      # 200, JSON with the DNS source
curl -s http://127.0.0.1:8010/api/v1/domain/10.0.0.1         # 400, {"error": ..., "input": ...}
curl -s http://127.0.0.1:8010/api/v1/health                  # {"status": "ok"}
```

Each source in the response has a `status`: `ok`, `not_found` (the source answered "nothing known") or
`error` (the check could not be completed). See [`design.md`](design.md) section 4 for the full contract.

## Test

```bash
python -m pytest
```

Milestone 1 tests cover input validation only and make no network calls. Recorded-response tests for the sources come in Milestone 2.

## Layout

```
backend/app/   main.py (API), validation.py, models.py, service.py, config.py, sources/doh.py
frontend/      app.py (Streamlit page), client.py (calls the backend only)
tests/         test_validation.py
docs/          interview.md, milestones.md, screenshots/
```
