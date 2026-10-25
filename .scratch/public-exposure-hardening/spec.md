# Public exposure hardening

Status: ready-for-agent

## Problem Statement

The owner wants the panel reachable at `harpi.smileydroid.com.br`, but the current build is not safe for a public subdomain. A member of any guild the bot shares can sign in and control playback in every guild the bot shares. The image carries the Discord token and the master YouTube cookie. The compose file publishes port 8000 and mounts the repository read-write. The login cookie has no `Secure` flag, lasts 30 days with sliding renewal, and cannot be revoked. The music source accepts any URL with a dotted host and hands it to yt-dlp, which fetches internal hosts.

Each of these is a remote path once the subdomain exists. The panel is meant for a small audience: up to 10 viewers across two guilds, The Nosbor's Hand and the RPG guild. The security work has to preserve that experience while removing the cross-tenant, secret, network, login, and SSRF paths.

## Solution

The panel becomes safe to expose in two gated phases. Phase 0 closes the five blockers before any DNS or proxy host exists: a clean image, no published port, allowlisted guilds with membership authorization, a revocable `__Host-` login cookie, and a YouTube-only URL policy backed by egress denial. Phase 1 adds the public-facing controls: security headers and CSP, OpenAPI disabled, rate limits and quotas, a single valid proxy host with the admin interface on Tailscale, and safe logs and retention. Phase 2 adds the operational loop: Discord alerts, local backups with a restore test, dependency and image scans, and an owner-only `!shutdown`.

The gate is explicit. No DNS record and no proxy host are created until every item in the release checklist is true. The existing `docs/security/public-exposure-plan.md` holds the evidence, the three sources per control, and the container probes behind each decision.

## User Stories

1. As a guild member, I want to sign in with Discord, so that I do not need a second account for the panel.
2. As a guild member outside the allowlist, I want a clear denial when I sign in, so that I know the panel is not open to my guild.
3. As a viewer in one allowlisted guild, I want to see only the guilds I belong to, so that I cannot see another guild's channels or playback.
4. As a viewer, I want every guild-scoped API call to check my membership, so that hiding a guild in the UI is not the only control.
5. As a viewer, I want an unauthorized guild to answer as not found, so that the API does not reveal which guilds exist.
6. As a viewer, I want my login cookie to be `Secure`, `HttpOnly`, `SameSite=Lax`, and scoped to the host, so that scripts and sibling subdomains cannot read or plant it.
7. As a viewer, I want my login to expire after seven days, so that an old cookie stops working even if I keep using the panel.
8. As a viewer, I want logout to invalidate every device, so that a copied cookie dies when I sign out.
9. As a viewer, I want a forged `Host` header to be rejected, so that host-header attacks do not reach the app.
10. As a viewer, I want to queue a YouTube link and see it play, so that the main panel flow still works after the URL policy lands.
11. As a viewer, I want a non-YouTube URL to be rejected with a clear error, so that I know the restriction before I wait for a failure.
12. As a viewer, I want a URL that resolves to a private address to be rejected, so that a public-looking hostname cannot reach the internal network.
13. As a viewer, I want a redirect to a private address to be rejected, so that a public URL cannot bounce into the internal network.
14. As a viewer, I want search and queue requests to be rate limited, so that one person cannot exhaust the bot for everyone.
15. As a viewer, I want the live stream to stay connected, so that playback state updates without a reload.
16. As a viewer, I want the stream count capped per user and per guild, so that many tabs do not exhaust the process.
17. As a bot owner, I want the app to listen only on the Docker network, so that the public internet cannot bypass the proxy.
18. As a bot owner, I want the proxy to reach the app by service name, so that the app port never appears on the host.
19. As a bot owner, I want the image to exclude `.env`, `cookies.txt`, logs, the database, and `.git`, so that an image leak does not expose the bot.
20. As a bot owner, I want the YouTube master cookie mounted read-only, so that yt-dlp cannot overwrite the source of truth.
21. As a bot owner, I want the Discord token and YouTube cookie rotated after the old image is gone, so that previous copies stop working.
22. As a bot owner, I want a valid certificate and forced HTTPS, so that login traffic is encrypted.
23. As a bot owner, I want HSTS without `includeSubDomains`, so that the other subdomains are not broken before they are all HTTPS.
24. As a bot owner, I want the proxy admin interface reachable only through Tailscale, so that the internet cannot brute force it.
25. As a bot owner, I want one proxy host for the panel, so that duplicate or deleted entries cannot route traffic to the wrong service.
26. As a bot owner, I want security headers and a CSP, so that clickjacking and script injection have less room.
27. As a bot owner, I want the OpenAPI document and documentation UIs disabled in production, so that the API surface is not advertised.
28. As a bot owner, I want `!shutdown` restricted to my Discord ID, so that a guild member cannot stop the bot.
29. As an operator, I want a 64 KB request body limit, so that a large JSON body cannot exhaust memory.
30. As an operator, I want `429` responses with `Retry-After`, so that clients can back off instead of retrying immediately.
31. As an operator, I want logs without tokens, cookies, or passwords, so that the logs are safe to keep and read.
32. As an operator, I want log rotation, so that `spam.log` cannot fill the disk.
33. As an operator, I want viewers and connection events deleted after 30 days, so that personal data does not accumulate.
34. As an operator, I want a Discord webhook alert for 401, 403, 429, 5xx, stream growth, and disk pressure, so that I learn about attacks without watching the panel.
35. As an operator, I want a daily local backup with a tested restore, so that a lost database is recoverable.
36. As an operator, I want the image and dependencies scanned in CI, so that known vulnerabilities are caught before release.
37. As a maintainer, I want the guild allowlist in the environment, so that changing it is explicit and auditable.
38. As a maintainer, I want an empty allowlist to deny every login, so that a missing configuration fails closed.
39. As a maintainer, I want the login epoch and allowed guilds in ordered migrations, so that schema changes are reproducible.
40. As a maintainer, I want the API contract regenerated, so that the client types and validators match the new behavior.
41. As a maintainer, I want tests at the HTTP seam with fake Discord and fake bot state, so that the behavior is proven without a live bot.
42. As a maintainer, I want the release checklist in the plan, so that "ready to expose" is an objective gate and not a judgment call.

## Implementation Decisions

### Configuration and admission

- The config module gains `panel_guild_allowlist`, a set of Snowflakes parsed from `PANEL_GUILD_ALLOWLIST`. The initial value is `734174030701264906,896066642948259960`.
- An empty or malformed allowlist denies every login. It must not fall back to "all bot guilds".
- The bot must be a member of every allowlisted guild. A guild in the allowlist without the bot is inert and its members are denied.
- The auth page computes the intersection of the user's guilds, the allowlist, and the bot's guilds. An empty intersection redirects to `/?auth=denied`.
- The same auth page persists the user's allowed guilds and records the user in the registry. The allowlist is the outer boundary, and the user's guild set is the inner boundary.
- Authorization is membership only. There is no DJ role and no `Manage Guild` requirement in this phase. Any member of an allowed guild may operate the player.
- `PANEL_PUBLIC_MODE` is a boolean config flag. It selects the YouTube-only URL policy. The LAN mode may broaden the policy later without changing the public behavior.

### Login and cookie

- The login cookie uses `__Host-harpi`, `Secure`, `HttpOnly`, `SameSite=Lax`, and `Path=/`. The `__Host-` prefix requires `Secure`, no `Domain`, and `Path=/`.
- The cookie lifetime is seven days absolute. `PERMANENT_SESSION_LIFETIME` is set to seven days and the app stops sliding the lifetime on every request.
- The cookie carries `issued_at` and the user's `login_epoch`. The epoch is global per user. Logout increments it, so every device is invalidated.
- The API guard rejects a login whose `issued_at` is older than seven days or whose epoch does not match the registry.
- The app sets `TRUSTED_HOSTS` to the public hostname and to `localhost` for the healthcheck. A forged `Host` header gets a 400 before routing.
- The auth callback clears the login state before establishing the new login and emits a fresh cookie.
- Local development over HTTP needs a flag that relaxes `Secure` and the `__Host-` prefix. The production default stays strict.

### Authorization and panel state

- The panel state gains an actor-aware guild visibility check. It answers whether a viewer may see and operate a guild, not merely whether the bot is in that guild.
- The guild list, channel list, selection, connect, disconnect, queue, layer, and transport paths all go through the same check.
- Unauthorized guilds answer `404 not_found`, matching the existing error envelope and avoiding an existence leak.
- The registry gains a `user_guilds` table keyed by user and guild, with a `seen_at` timestamp, and a `login_epoch` column on `users`.
- The migrations are ordered and additive. Existing users start at epoch zero. The first login after the migration records their guilds.

### URL policy and SSRF

- A new source-policy module owns the URL decision. It exposes pure functions for scheme and host checks, DNS resolution checks, and redirect checks, so the policy is testable without yt-dlp.
- In public mode, only YouTube and its CDN are accepted. yt-dlp's `allowed_extractors` is restricted to `youtube`, `youtube:tab`, and `youtube:search`.
- The policy rejects loopback, RFC1918, link-local, multicast, IPv6 loopback, and the cloud metadata address, both before the request and after each redirect.
- The policy rejects hostnames that resolve to a private address, including wildcard DNS services such as `sslip.io` and `nip.io`.
- Playlists are limited to one item in public mode. Extraction time, duration, and size limits stay bounded.
- The container runs on a network with an egress deny for private ranges. The policy and the network control are independent, so a parser bypass does not become network access.

### Deployment and proxy

- The compose service publishes no host port. NPM and Harpi join the `harpi-edge` network, and the proxy forwards to `harpi-backend:8000`.
- Only `data/`, a writable work directory, and `cookies.txt` are mounted. `cookies.txt` is read-only. The repository is not mounted into the runtime container.
- The image builds from a clean context. The Docker ignore file excludes `.env*`, `cookies.txt`, logs, the database, `.git`, `.scratch`, tests, and build caches.
- The runtime container keeps the non-root user, drops capabilities, sets `no-new-privileges`, uses a read-only root filesystem with a writable `/tmp`, and sets PID and memory limits. The cookie working copy, yt-dlp scratch files, and the rotated log file live in the writable work directory, not in the image root.
- The runtime command runs the prebuilt virtualenv entry point, so a read-only root does not trigger a dependency sync.
- NPM serves one proxy host with a valid Let's Encrypt certificate, forced HTTPS, HTTP/2, HSTS without `includeSubDomains`, and WebSocket upgrade.
- The NPM admin interface binds to the Tailscale address or is blocked by the host firewall. Port 81 is not reachable from the public interface.
- The DNS stays at Registro.br and points directly at the host. Cloudflare is not in the path in this phase.

### Application surface

- The app adds a security-header response hook for HSTS, `X-Content-Type-Options`, `Referrer-Policy`, `Permissions-Policy`, `Cross-Origin-Opener-Policy`, `Cross-Origin-Resource-Policy`, `X-Frame-Options`, and CSP.
- The first CSP allows the inline SvelteKit bootstrap and the Google Fonts origins. The follow-up moves fonts to the app origin and uses a build-time hash for the inline script.
- The OpenAPI document, Swagger UI, Redoc, and Scalar endpoints are disabled in production. The contract export continues to read the provider directly.
- The request body limit is 64 KB. The app answers `413` above the limit.
- The proxy rate limits are 10 requests per minute per IP for auth and 60 per minute per IP for the rest of the API. The app adds per-user limits: 20 searches per minute and a queue token bucket.
- The SSE stream is capped at five connections per user and twenty per guild. The sampler keeps its one-poll-per-guild design.
- The proxy hides the `Server` header and disables server tokens.

### Logging, retention, and operations

- Loguru writes to stdout and to a rotated file under the writable work directory, keeps a bounded number of files, and logs at INFO in production. yt-dlp runs quiet, without verbose request headers.
- URL, token, cookie, and authorization values are redacted before logging. The security log records login, login failure, logout, access denial, selection changes, and 5xx with user id, IP, and UTC time.
- The database file is mode 600. Backups use the SQLite backup API or a WAL checkpoint, not a raw copy of the live file.
- A retention job deletes viewers and connection events older than 30 days.
- `!shutdown` checks the bot owner's Discord ID and refuses everyone else.
- A Discord webhook in a private channel receives alerts for 401, 403, 429, 5xx, SSE growth, and disk pressure. The webhook URL is a secret in the root-only environment.
- CI runs `gitleaks`, `osv-scanner`, and `trivy image`. Base images are pinned by digest. Dependabot or Renovate keeps the lockfiles current.

## Testing Decisions

A good test drives the app at its external seam and asserts behavior a viewer or operator can observe. It does not reach into private helpers or assert call order inside a module. The existing suite already uses the Quart test client with fake Discord, fake bot, fake guilds, and fake playback sessions, so the new behavior should follow that shape.

The primary seam is the app's HTTP surface. The auth tests fake `discord_oauth._fetch_json` and let the real guild admission and registry code run. The API tests inject a fake bot and fake playback session and assert status codes, envelopes, and state. New tests for the allowlist, cross-tenant denial, cookie flags, epoch invalidation, headers, disabled docs, body limit, and rate-limit envelopes belong at this seam.

The URL policy gets one new pure-function seam. It takes a URL and a resolver, and returns allow or deny with a reason. Tests cover YouTube, a non-YouTube public host, a hostname that resolves to loopback, a hostname that resolves to RFC1918, the metadata address, and a redirect to a private address. The yt-dlp wiring test asserts that the configured `allowed_extractors` and playlist limits are the public-mode values.

The registry gets a schema seam. Tests run the migrations against a temporary database, assert the new tables and columns, record allowed guilds, read them back, increment the login epoch, and run the retention cleanup with rows older and newer than 30 days.

Prior art lives in the auth HTTP tests, the API tests, the storage tests, the config tests, and the music data tests. The design-language tests are not relevant here. The network tests stay out of the offline gate.

The release gate also runs the container probes from the security plan: unauthenticated API answers 401, OpenAPI answers 404, the login cookie carries `__Host-` and `Secure`, the SSRF probe is blocked, and the host exposes only 80 and 443. Those probes are integration checks, not pytest units.

## Out of Scope

- Cloudflare, a WAF, or a tunnel. The DNS stays at Registro.br.
- A paid external penetration test.
- Redis or a separate session store.
- A panel screen for editing the guild allowlist. The environment variable is the interface.
- DJ roles, `Manage Guild`, or per-user permissions inside an allowed guild.
- Non-YouTube sources in public mode. The LAN mode may add them later.
- High availability, multiple app instances, or horizontal scaling.
- Changing the public hostname.
- Automatic rotation of the Discord token or YouTube cookie. The runbook covers the manual rotation.
- A full container orchestration platform. The scope is the existing compose deployment.

## Further Notes

The evidence and the three-source matrix live in `docs/security/public-exposure-plan.md`. The five P0 findings are the image secret leak, the published port and read-write mount, the cross-tenant authorization gap, the insecure and irrevocable login cookie, and the yt-dlp SSRF.

The decisions recorded with the owner are: login and cookie terminology, an allowlist of The Nosbor's Hand and the RPG guild, membership-only authorization, YouTube-only URLs in public mode, the `harpi-edge` Docker network, a `__Host-` cookie with a global `login_epoch`, `harpi.smileydroid.com.br` without `includeSubDomains`, up to 10 viewers and 2 guilds, the checklist plus automated tests and an external port scan, the allowlist in the environment with a restart, a global logout, the NPM admin on Tailscale, DNS at Registro.br, root-only environment secrets, Discord alerts plus local backups, an owner-only `!shutdown`, and 30-day retention.

The audit harness is the `harpi-sec-audit` container built from the commit under review, with no published ports and no network. It reproduces the route, cookie, header, and SSRF probes. The SSRF probe uses a local hostname that resolves to `127.0.0.1` and checks that no request reaches the local server.

`make format` and `make check` remain the completion gate. The contract is regenerated after the API behavior changes, and the design-language tests must stay green because the panel's visual language does not change.
