# Release gate: public exposure

This is the checklist that decides whether `harpi.smileydroid.com.br` may exist. No DNS record and no proxy host are created until every item below passes. A record or a host created early makes a half-hardened panel reachable, and the script cannot undo that.

The automated part is `deploy/release-gate.sh`. It changes no configuration, DNS record, proxy host, or container. The operator part is the evidence each command leaves behind.

## Run the script

Three modes, one at a time:

```sh
deploy/release-gate.sh --pre
deploy/release-gate.sh --release --base-url https://harpi.smileydroid.com.br
deploy/release-gate.sh --ports harpi.smileydroid.com.br
```

`--pre` runs before the DNS record and the proxy host exist. `--release` runs after the certificate is issued and the host answers. `--ports` runs from outside the host network.

Each check prints one line beginning with `PASS`, `FAIL`, or `SKIP`. The last line is the verdict. The verdict is `PASS` only when every check passed. `FAIL` and `INCOMPLETE` exit 1. A `SKIP` makes the run `INCOMPLETE`, because an unproven item is not a pass.

| Variable | Use |
| --- | --- |
| `HARPI_SESSION_COOKIE` | The login cookie header (`__Host-harpi=...`) or its value. Without it the two authenticated probes report `SKIP`. |
| `NPM_TOKEN` | Optional. `--pre` reads the NPM proxy-host list instead of the rendered configs. |
| `NPM_CONTAINER` | NPM container name for the rendered-config read. Default `nginx-app-1`. |
| `NPM_URL` | NPM admin base URL. Default `http://100.106.27.40:81`. |
| `SCAN_PORTS` | Ports the external scan covers. Default `-`, every TCP port. Set a list such as `22,80,81,111,443,8000,8096,52082` for a faster targeted scan. |
| `TIMEOUT` | Per-request timeout in seconds. Default `10`. |
| `SEARCH_TIMEOUT` | Timeout for the YouTube probe. Default `60`. |
| `PYTHON` | Interpreter for the helpers. Default `ROOT/.venv/bin/python`, then `python3`. It must be 3.13 or newer. |

`--pre` needs either `NPM_TOKEN` or read access to the NPM container. Without either it fails closed, because it cannot prove no proxy host exists. Its public probe uses `curl -k`, because the question is whether anything answers on 80 or 443, not whether the certificate is trusted. `--release` and `verify-proxy.sh` check trust.

## What the script proves

| Check | Mode | Passes when |
| --- | --- | --- |
| `dns` | `--pre` | no A or AAAA record answers for the public name |
| `proxy host` | `--pre` | no NPM host and no rendered config claims the name |
| `public host` | `--pre` | neither `http://` nor `https://` answers |
| `unauthenticated /api/session` | `--release` | the status is 401 |
| `hsts` | `--release` | `Strict-Transport-Security` has a positive `max-age` and no `includeSubDomains` |
| `/openapi.json` | `--release` | the status is 404 |
| `/docs` | `--release` | the status is 404 |
| `/redocs` | `--release` | the status is 404 |
| `/scalar` | `--release` | the status is 404 |
| `login cookie` | `--release` | the name has the `__Host-` prefix and the cookie carries `Secure`, `HttpOnly`, `SameSite=Lax`, `Path=/`, and no `Domain` |
| `ssrf queue probe` | `--release` | `POST /api/queue` with `http://169.254.169.254/latest/meta-data/` answers 400 |
| `youtube url accepted` | `--release` | `POST /api/search` with a normal YouTube URL answers 200 |
| `open ports` | `--ports` | only 80 and 443 are open |

The SSRF probe needs an authenticated session with a live playback session, because the queue route answers 404 before it reaches the URL policy. Sign in, connect the bot to a voice channel, and pass the cookie. A 404 is reported as a failure, not a skip.

The YouTube probe uses `/api/search`, not `/api/queue`, so an accepted URL does not change the queue. The private-address probe uses `/api/queue` because that is the route the plan names. The policy refuses it before the queue is touched.

`--release` reports `SKIP` for both authenticated probes only when `HARPI_SESSION_COOKIE` is unset. A skip is not a pass. Record the reason and run the probe again with a cookie before ticking the item.

## Checklist

Every item maps to the command that proves it. Run the command, keep the output, then tick the item.

| Item | Command | Evidence |
| --- | --- | --- |
| The image carries no `.env`, `cookies.txt`, logs, database, or `.git`. | `docker run --rm --entrypoint sh IMAGE -c 'ls /app/.env /app/cookies.txt /app/data/harpi.db; find /app -maxdepth 1 -name "*.log"'` then `make security` | only missing-path errors, scanners clean |
| The Discord token and YouTube cookie were rotated after the last old image. | operator action in [runbook-secret-rotation.md](runbook-secret-rotation.md) | rotation date, old token answers 401 |
| Port 8000 is not published on the host. | `docker inspect harpi-backend --format '{{json .HostConfig.PortBindings}}'` | `{}` |
| NPM and Harpi share `harpi-edge`, and the proxy forwards to `harpi-backend:8000`. | `docker network inspect harpi-edge --format '{{range .Containers}}{{.Name}} {{end}}'` and `NPM_IDENTITY=... NPM_PASSWORD=... deploy/npm-proxy-host.sh --check` | `harpi-backend nginx-app-1`, one host |
| The allowlist is configured and a login outside it is denied. | `docker compose exec backend printenv PANEL_GUILD_ALLOWLIST` and `uv run pytest tests/test_auth.py -q -k 'outside_the_allowlist or allowlist_is_empty or allowlist_is_malformed'` | the two ids, passing tests |
| The allowlist comes from `PANEL_GUILD_ALLOWLIST` and needs a restart. | the `printenv` above, then restart and repeat | same value before and after |
| A user of guild A gets 403 or 404 for guild B. | `uv run pytest tests/test_api.py -q -k 'another_actors_guild or unshared_guild'` | passing tests |
| The login cookie has `__Host-`, `Secure`, `HttpOnly`, `SameSite=Lax`, and `Path=/`, with no `Domain` and a seven-day lifetime. | `deploy/release-gate.sh --release --base-url https://harpi.smileydroid.com.br` and `uv run pytest tests/test_auth.py -q -k 'login_issues_a_host_only_secure_cookie or login_cookie_expires_in_seven_days'` | the `login cookie` line, passing tests |
| Logout invalidates every device through `login_epoch`. | `uv run pytest tests/test_auth.py -q -k logout_revokes_a_replayed_cookie` | passing test, replayed cookie answers 401 |
| Secrets live in `.env` with mode 600 outside the build. | `stat -c '%a %n' .env` and `git check-ignore -v .env` and `docker run --rm --entrypoint sh IMAGE -c 'test ! -e /app/.env'` | `600`, ignored, absent |
| Internal URLs, private addresses, and redirects to private addresses are refused. | `deploy/release-gate.sh --release --base-url https://harpi.smileydroid.com.br` and `uv run pytest tests/test_source_policy.py -q` | the `ssrf queue probe` line, passing tests |
| `/openapi.json`, `/docs`, `/redocs`, and `/scalar` do not answer in production. | `deploy/release-gate.sh --release --base-url https://harpi.smileydroid.com.br` | four `404` lines |
| Security headers and CSP are present. | `curl -sS -D - -o /dev/null https://harpi.smileydroid.com.br/ \| grep -iE 'strict-transport\|content-security\|x-content-type\|referrer-policy\|permissions-policy\|x-frame'` | the header lines |
| Rate limits answer 429 and the body cap answers 413. | `deploy/check-rate-limits.sh` and `uv run pytest tests/test_api.py -q -k body_above_the_limit` | 429 in each burst, passing test |
| The certificate is valid, the proxy host is unique, and HSTS has a positive `max-age` without `includeSubDomains`. | `deploy/verify-proxy.sh` and the `--release` run | issuer, expiry, one host, the `hsts` line |
| The NPM admin port 81 answers only over Tailscale. | `deploy/check-admin-exposure.sh` | public silent, Tailscale answers |
| SSH, rpcbind, Jellyfin, and qBittorrent do not answer on the internet. | `deploy/release-gate.sh --ports harpi.smileydroid.com.br` | only 80 and 443 open |
| `!shutdown` is owner-only. | `uv run pytest tests/test_basic_cog.py -q -k shutdown` | passing tests |
| The 30-day retention is configured. | `uv run pytest tests/test_retention.py -q` | passing tests |
| Discord alerts and the local backup were tested. | `docker compose exec -w /app backend /app/.venv/bin/python -m tools.backup_db verify` and one unauthenticated API call | counts match, the `401 unauthorized` message arrives |
| Logs carry no token, cookie, or password. | `uv run pytest tests/test_redaction.py tests/test_logging_setup.py -q` and `docker compose logs --tail=200 backend \| grep -iE 'token\|cookie\|authorization'` | passing tests, no value in the output |
| The backup and its restore were tested. | `docker compose exec -w /app backend /app/.venv/bin/python -m tools.backup_db verify` | matching `users`, `viewers`, and `connection_events` counts |
| `make check` is green and the contract is regenerated. | `make check` and `git diff --exit-code -- web/src/lib/contract` | exit 0, no contract diff |
| The DNS name and the proxy host did not exist before the gate passed. | `deploy/release-gate.sh --pre` before step 2 of [runbook-public-host.md](runbook-public-host.md) | the three `--pre` lines, all `PASS` |

## Operator-only items

No script proves these. Record the person, the date, and what was observed.

| Item | What the operator does |
| --- | --- |
| Certificate issued | Confirm in the NPM UI that the certificate is the Let's Encrypt one for this hostname, and record its expiry. `verify-proxy.sh` reads the presented chain but cannot see which NPM certificate was attached. |
| Backup restored | Restore a backup over a copy of the database, start the panel against it, and confirm the same users and presence. `tools.backup_db verify` compares counts but does not run the panel. |
| Alert delivered | Send an unauthenticated API call and confirm the message reaches the private Discord channel. The webhook is real state that no offline test covers. |
| Discord OAuth exercised with a real bot | Sign in with a real Discord account, in an allowlisted guild, with the bot online. The tests fake Discord and cannot prove the real client id, redirect URI, and bot membership. |
| Token and cookie rotation | Follow [runbook-secret-rotation.md](runbook-secret-rotation.md) and confirm the old values are rejected. |
| Cross-guild denial with two accounts | Sign in as a member of each allowlisted guild and confirm the other guild answers 404 in the panel. The API tests fake both actors. |
| `!shutdown` with a real member and the owner | Run it from a non-owner account, then from the owner account. The unit tests cover the check, not the live bot. |

## Record the result

Append the full output of every command to `.scratch/public-exposure-hardening/issues/14-release-gate.md` with the release commit, the date, the certificate expiry, and the reason for any `SKIP`. Tick a box in [public-exposure-plan.md](public-exposure-plan.md#gate-de-liberação) only when its own evidence exists.

The order is fixed:

1. Every `make check` and container probe is green.
2. `deploy/release-gate.sh --pre` passes and is recorded.
3. The DNS record is created at Registro.br.
4. The proxy host is created and the certificate is issued.
5. `deploy/release-gate.sh --release` and `deploy/release-gate.sh --ports` pass and are recorded.
6. The operator-only items are recorded.

Step 3 and step 4 never come before step 2.
