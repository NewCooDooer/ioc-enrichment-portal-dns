# Planning interview (Claude ↔ Evan), 2026-11-05

Claude interviewed me one question at a time before drafting `design.md`. Questions are in the order asked.
**"Changed the design"** marks the three I will submit.

| # | Question | My answer | Effect on design |
|---|---|---|---|
| 1 | Who calls the portal, and how? | Analyst UI **plus other programs** | **Changed the design.** The API contract becomes the product: versioned `/api/v1/`, one stable error format, per-source status, ports configurable. The UI is just one client. |
| 2 | Which three sources for DNS names? | **DoH + RDAP + crt.sh** (all keyless) | **Changed the design.** No keys in v1, so section 8 is mostly about *values* that must not leave the machine. It also forced a crt.sh failure plan: it returned HTTP 502 during live testing. |
| 3 | Which stack? | **FastAPI + Streamlit** | Async fan-out to three sources; typed models for the contract; pure-Python frontend. |
| 4 | How do tests replay real responses? | **Saved JSON fixtures + respx** | No cassettes, no recorded headers, so keys cannot leak into recordings. |
| 5 | How does a failed source appear? | **Per-source status block, HTTP 200**; 502 only if all fail | **Changed the design.** Adds `ok` / `not_found` / `error` with `error.code`, so callers can tell "no data" from "source failed", and partial results survive. |
| 6 | Repo name | `ioc-enrichment-portal-dns`, public | Instructor must be able to read it. |
| 7 | Ports | Backend **8010**, frontend **8510** | Avoids 8000/8501 clashes when two portals run on one laptop. |
| 8 | Input scope | Strict FQDN, lowercase, IDN → punycode; reject IPs and URLs | Defines the 400 behavior and echoes both original and normalized input. |

Not decided yet (kept as open questions in `design.md`): Cloudflare DoH fallback, extra record types, crt.sh terms.
