# IOC Enrichment Portal: DNS names

A SOC lookup tool: enter a DNS name and see enrichment from three real, keyless sources
(Google DNS over HTTPS, RDAP, crt.sh) in one place. Python only: a FastAPI backend and a separate Streamlit frontend.

**Status:** Milestone 0 (design). No code yet. See [`design.md`](design.md) for the plan, API contract and
milestone definitions of done, [`docs/interview.md`](docs/interview.md) for the planning interview, and
[`docs/milestones.md`](docs/milestones.md) for progress and evidence.

> **Do not enter internal or private names** (for example `*.corp`, `*.local`, your company's own domains).
> Lookups go to outside services (Google, Verisign and other registries, Sectigo's crt.sh). A guard comes in a later milestone.

Install and run instructions arrive with Milestone 1.
