# Security

The panel drives playback, so the web surface is hostile territory: `.env` and
the YouTube cookie are the only secrets, and the panel goes public only after
the gate in [runbook.md](runbook.md) passes. The audit that produced this
baseline is in the git history.

| Topic | Decision |
| --- | --- |
| Admission | Guild allowlist from `PANEL_GUILD_ALLOWLIST`; anyone in an allowed guild operates the player. No DJ role. |
| Login | Discord OAuth2 + PKCE (ADR 0007); `__Host-harpi`, `Secure`, `HttpOnly`, `SameSite=Lax`, seven days, `login_epoch` revocation. |
| URLs | Public mode allows YouTube and its CDN only; private, link-local and metadata addresses are refused after DNS resolution, on every redirect hop. |
| Network | NPM and Harpi on `harpi-edge`; no published host port; `DOCKER-USER` denies egress to private ranges. |
| Proxy | HSTS without `includeSubDomains`; admin UI on 81 over Tailscale only. |
| Limits | `limit_req` per IP, app token buckets, 64 KB body cap, 5 streams per user, 20 per guild. |
| Retention | 30 days for viewers and connection events; daily backup with a restore check, newest seven kept. |
| Alerts | Private webhook for 401, 403, 429, 5xx, SSE growth and disk pressure, coalesced 60 s. |
| Logs | Rotated, redacted; `security.log` carries login, denial, selection and 5xx with user id, IP and UTC time, never a body. |
| Capacity | 10 viewers, 2 guilds. |

[scanners.md](scanners.md) covers gitleaks, osv-scanner and trivy.
