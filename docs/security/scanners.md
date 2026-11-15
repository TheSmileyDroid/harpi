# CI scanners

`.github/workflows/security.yml` runs on push to `main`, on PRs, weekly and on
demand. Every job fails the workflow on a finding, with `contents: read` and no
repository secret. Actions are pinned by SHA and images by digest; the pins
live in the workflow and the `Dockerfile`, not here.

| Job | Tool | Input | Fails on |
| --- | --- | --- | --- |
| Secret scan | gitleaks | full git history | any committed value matching a rule |
| Dependency scan | osv-scanner | `uv.lock`, `web/bun.lock` | a locked version with a known advisory |
| Image scan | trivy | the built image | HIGH/CRITICAL CVE with a fix available |

The image scan is the backstop for the lockfile: `uv sync --frozen` installs
exactly what `uv.lock` records, and `apt-get upgrade` patches Debian. Bun
dependencies never reach the image, so osv-scanner is their only check.
Dependabot opens weekly version PRs for `uv`, `bun`, Docker and actions; Bun
security updates arrive through osv-scanner only.

None of the three looks at request handling. SSRF, cross-guild authorization,
cookie flags, rate limits and headers are covered by `tests/` and the release
gate, not by a scanner.

## Triage

1. Read the job log: gitleaks prints rule, file, commit and a redacted match;
   osv-scanner and trivy print package, installed, fixed and advisory id.
2. Reproduce locally with `make security` (runs whatever is on `PATH`) and
   `trivy image harpi:local`.
3. A leaked secret is live: rotate it with the steps in
   [runbook.md](runbook.md), then remove it from history.
4. Fix a dependency with `make bootstrap`, or move the base image digest.
   `ignore-unfixed` means a failing CVE has a fix available.
5. Never lower a severity or drop a scanner step to go green.

Test fixtures and vendored placeholders get a narrow entry, never a rule-wide
allowlist:

| File | Current entries |
| --- | --- |
| `.gitleaks.toml` | the fake key in `tests/test_redaction.py`, the RFC 6455 sample nonce in the runbook, the public client id in `tests/test_config.py` |
| `osv-scanner.toml` | `PYSEC-2026-3002` (discord.py pins pynacl below 1.6) and two SvelteKit advisories that need prerendering or `use:enhance`; expire 2027-01-31 |
| `.trivyignore.yaml` | the placeholder AWS key yt-dlp ships in `extractor/shahid.py` |
