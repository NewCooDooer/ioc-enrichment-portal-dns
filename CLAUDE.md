# Instructions for Claude Code

- Read `design.md` before changing the API, adding a source, or adding any feature. It lists what is out of scope.
- Update `design.md` and `README.md` in the same change as the code they describe.
- Backend and frontend are separate; the frontend must only call the backend, never a source.
- Never put keys, tokens or secrets in code, fixtures or commits. Never upload files to VirusTotal.
- Tests must replay recorded fixtures and make no network calls.
- Log milestone evidence in `docs/milestones.md`. One branch and one pull request per milestone.
