# Runbook: putting Harpi on the internet

Nothing here has been run. Order is fixed: gate, network, DNS, proxy,
certificate, admin lockdown, verification. A DNS record or proxy host created
early makes a half-hardened panel reachable. Decisions: [README.md](README.md).
Scanners: [scanners.md](scanners.md).

## 1. Edge network and egress deny

Harpi publishes no host port; NPM reaches it as `harpi-backend:8000` over the
external `harpi-edge` network, and `DOCKER-USER` denies egress to private
ranges.

```sh
docker network inspect harpi-edge >/dev/null 2>&1 || docker network create harpi-edge
```

Add to the NPM service in `/home/opc/external/nginx/docker-compose.yml`:

```yaml
services:
  app:
    networks: [npm_proxy, harpi-edge]
networks:
  npm_proxy: { external: true, name: "robsons" }
  harpi-edge: { external: true }
```

```sh
cd /home/opc/external/nginx && docker compose up -d app   # drops every site briefly
cd /path/to/harpi && docker compose up -d backend
sudo ./deploy/egress-deny.sh print   # renders, changes nothing
sudo ./deploy/egress-deny.sh apply   # inserts what is missing, idempotent
```

The rules drop `127/8`, `10/8`, `172.16/12`, `192.168/16`, `169.254/16` and
`224/4` for each container address, plus `::1`, `fc00::/7`, `fe80::/10`,
`ff00::/8` over `ip6tables`. Re-run `remove` then `apply` after a recreate.

```sh
sudo ss -tlnp | grep -E ':(80|443|8000)\b'                      # only 80, 443
docker inspect harpi-backend --format '{{json .HostConfig.PortBindings}}'  # {}
docker run --rm --network harpi-edge alpine:3.20 wget -qO- -T 3 http://harpi-backend:8000/ | head -c 120
docker exec harpi-backend sh -c 'curl -sS --max-time 3 http://169.254.169.254/; echo "exit=$?"'  # 28
docker exec harpi-backend sh -c 'curl -sS -o /dev/null -w "%{http_code}\n" https://www.youtube.com/'  # 200/301
```

`DOCKER-USER` sees forwarded traffic only, so host-owned addresses stay
outside. Rules do not survive reboot; re-apply. If `resolv.conf` shows an
RFC1918 resolver, add an `ACCEPT` above the drops.

## 2. Public host

### 2.1 Gate

```sh
docker inspect harpi-backend --format '{{json .HostConfig.PortBindings}}'
docker network inspect harpi-edge --format '{{range .Containers}}{{.Name}} {{end}}'
sudo ss -tlnp | grep -E ':(80|443|8000)\b'
```

Expected `{}`, `harpi-backend nginx-app-1`, only 80/443. Stop while any is
wrong or any [checklist](#gate-checklist) box is unticked.

### 2.2 DNS

One A record at Registro.br: `harpi` → host public IPv4, TTL 3600. No
wildcard, no Cloudflare. `AAAA` only when IPv6 works end to end. Wait for
`dig +short A harpi.smileydroid.com.br` before the certificate.

### 2.3 Proxy host

```sh
deploy/npm-proxy-host.sh                                  # prints, writes nothing
NPM_IDENTITY=you@example.com NPM_PASSWORD='...' deploy/npm-proxy-host.sh --apply
```

One host for the public name → `harpi-backend:8000` over `http`, exploits
blocked, caching off, WebSocket on, Advanced tab from
`deploy/npm/harpi-advanced.conf` (`server_tokens off`, `proxy_buffering off`,
64 KB body cap, 429 with `Retry-After`, `limit_req` per IP on `/api/auth/` and
`/api/`). `proxy_set_header Host $host` keeps the trusted-host check on the
public name. Zones live in `deploy/npm/harpi-rate-limits-http.conf`, installed
as `http_top.conf` (NPM parses `proxy_host/*.conf` before `http.conf`):

```sh
install -m 644 deploy/npm/harpi-rate-limits-http.conf /home/opc/external/nginx/data/nginx/custom/http_top.conf
docker exec nginx-app-1 nginx -t && docker exec nginx-app-1 nginx -s reload
```

### 2.4 Certificate

```sh
NPM_IDENTITY=you@example.com NPM_PASSWORD='...' deploy/npm-proxy-host.sh --apply --certificate new
```

HTTP-01 over port 80, then the host is rewritten with the certificate and
forced HTTPS, HTTP/2 and HSTS (no `includeSubDomains`). Re-running reuses it;
`--certificate <id>` attaches one from the UI.

### 2.5 Admin on Tailscale

```yaml
    ports: ['80:80', '100.106.27.40:81:81', '443:443']
```

```sh
cd /home/opc/external/nginx && docker compose up -d app
curl -sS -o /dev/null -w 'public=%{http_code}\n' --max-time 5 http://PUBLIC_IP:81/      # 000
curl -sS -o /dev/null -w 'tailscale=%{http_code}\n' --max-time 5 http://100.106.27.40:81/
```

### 2.6 fail2ban

NPM logs the admin access log to `/dev/null`, so failed admin logins leave no
trace. `deploy/npm/admin-production.conf` is the NPM 2.12.6 admin block with
`access_log /data/logs/admin_access.log standard;`. Mount it writable
(`:ro` aborts the start, NPM's IPv6 script edits `conf.d`):

```yaml
    volumes: ['./admin-production.conf:/etc/nginx/conf.d/production.conf']
```

```sh
sudo mkdir -p /var/log/npm
sudo mount --bind /home/opc/external/nginx/data/logs /var/log/npm
grep -q '/var/log/npm' /etc/fstab || echo '/home/opc/external/nginx/data/logs /var/log/npm none bind 0 0' | sudo tee -a /etc/fstab
sudo semanage fcontext -a -t var_log_t '/home/opc/external/nginx/data/logs(/.*)?'
sudo restorecon -R /home/opc/external/nginx/data/logs
sudo deploy/fail2ban/install.sh
```

Jails: `npm-admin-auth` (failed `POST /api/tokens` 401/403),
`harpi-auth` (failed `/api/auth/` 401/403), `sshd`. Both proxy jails ban
through `npm-docker-user` (a `DROP` in `DOCKER-USER`; the stock action writes
`INPUT`, which never sees Docker traffic) and write `iptables` only.

```sh
sudo fail2ban-client status npm-admin-auth && sudo fail2ban-client status harpi-auth
```

## 3. Alerts, backups, rotation

`PANEL_ALERT_WEBHOOK` in the root-only `.env` (mode 600); empty means no-op.
Alerts: 401, 403, 429, 5xx, SSE growth (15 streams), disk pressure (85%),
coalesced for 60 s on a bounded queue of 32.

- **401/403** — `security event=access_denied` in `security.log`; a sustained
  stream from one address is probing, block it at the proxy.
- **429** — proxy rejections never reach the app; read the NPM access log.
- **5xx** — `harpi.log` traceback; restart once, a repeat is code or data.
- **SSE growth** — many tabs is fine; one address looping is abuse.
- **Disk** — `df -h`, prune logs and old backups, grow the volume.

Rotate the webhook: recreate it in the channel, replace the value, then
`docker compose up -d --force-recreate backend`, and confirm with one
unauthenticated call.

Backups: one at startup and every 24 h through the SQLite backup API, under
`HARPI_WORK_DIR/backups`, mode 600, newest seven kept.

```sh
docker compose exec -w /app backend /app/.venv/bin/python -m tools.backup_db backup
docker compose exec -w /app backend /app/.venv/bin/python -m tools.backup_db verify
```

Restore: verify, `docker compose stop backend`, copy the file over
`data/harpi.db`, `rm -f data/harpi.db-wal data/harpi.db-shm`, `chmod 600`,
start, sign in once, verify again.

Rotation, after the new image is scanned: reset the Discord token, replace
`DISCORD_TOKEN`, `docker compose up -d --force-recreate backend`; replace
`cookies.txt` (mode 600), `docker compose restart backend`, then compare the
`cookie master sha256=` startup line with `sha256sum cookies.txt`.

```sh
docker compose exec backend touch /app/cookies.txt   # must fail: read-only
docker compose exec backend test -w /work            # must succeed
docker run --rm --entrypoint sh IMAGE -c 'ls /app/.env /app/cookies.txt /app/data; find /app -maxdepth 1 -name "*.log"'
```

## 4. Verification

`tools/release_gate.py` changes nothing. Three modes, one at a time:

```sh
uv run python tools/release_gate.py --pre
uv run python tools/release_gate.py --release --base-url https://harpi.smileydroid.com.br
uv run python tools/release_gate.py --ports harpi.smileydroid.com.br
```

Each check prints `PASS`, `FAIL` or `SKIP`; the verdict is `PASS` only when
all passed, and a `SKIP` makes the run `INCOMPLETE`. `HARPI_SESSION_COOKIE`
unlocks the authenticated probes, `NPM_TOKEN` the proxy-host list,
`SCAN_PORTS` narrows the port scan, `PYTHON` picks the interpreter (3.13+).

| Check | Mode | Passes when |
| --- | --- | --- |
| `dns`, `proxy host`, `public host` | `--pre` | nothing answers, no host claims the name |
| `unauthenticated /api/session` | `--release` | 401 |
| `authenticated session` | `--release` | 200 with the cookie |
| `hsts` | `--release` | positive `max-age`, no `includeSubDomains` |
| docs routes | `--release` | `/openapi.json`, `/docs`, `/redocs`, `/scalar` all 404 |
| `login cookie` | `--release` | `__Host-`, `Secure`, `HttpOnly`, `SameSite=Lax`, no `Domain` |
| `ssrf queue probe` | `--release` | queueing `http://169.254.169.254/` answers 400 |
| `youtube url accepted` | `--release` | search with a YouTube URL answers 200 |
| `open ports` | `--ports` | only 80 and 443 |

One-time proxy reads:

```sh
openssl s_client -connect harpi.smileydroid.com.br:443 -servername harpi.smileydroid.com.br \
  -verify_return_error </dev/null 2>/dev/null | openssl x509 -noout -issuer -enddate -checkend 1209600
curl -sS -o /dev/null -w '%{http_code} %{redirect_url}\n' http://harpi.smileydroid.com.br/   # 301/308
curl -sS -D - -o /dev/null https://harpi.smileydroid.com.br/ | grep -iE 'strict-transport-security|^server:'
curl --http2 -sS -o /dev/null -w '%{http_version}\n' https://harpi.smileydroid.com.br/       # 2
curl -sS --http1.1 -o /dev/null -w '%{http_code}\n' -H 'Connection: Upgrade' -H 'Upgrade: websocket' \
  -H 'Sec-WebSocket-Version: 13' -H 'Sec-WebSocket-Key: dGhlIHNhbXBsZSBub25jZQ==' https://harpi.smileydroid.com.br/  # 101/400
for i in $(seq 1 20); do curl -sS -o /dev/null -w '%{http_code} ' https://harpi.smileydroid.com.br/api/auth/discord; done; echo  # a 429
```

### Gate checklist

| Item | Command |
| --- | --- |
| Image carries no `.env`, cookie, logs, db, `.git` | the `docker run ... ls` above and `make security` |
| Token and cookie rotated after the old image | rotation steps; old token answers 401 |
| Port 8000 unpublished | `docker inspect ... PortBindings` → `{}` |
| Both containers on `harpi-edge` | `docker network inspect harpi-edge` |
| Allowlist set, outsider denied | `printenv PANEL_GUILD_ALLOWLIST`, `pytest -k allowlist` |
| Guild A gets 403/404 for guild B | `pytest tests/test_api.py -k 'another_actors_guild or unshared_guild'` |
| Cookie host-only, secure, revocable | `--release` and `pytest tests/test_auth.py -k 'cookie or logout'` |
| Secrets in `.env` mode 600, outside build | `stat -c '%a %n' .env`, `git check-ignore -v .env` |
| Private URLs and redirects refused | `--release` and `pytest tests/test_source_policy.py` |
| Docs routes 404 | `--release` |
| Security headers present | `curl -D - ... \| grep -iE 'strict-transport\|content-security\|x-frame'` |
| 429 and 413 | the burst above and `pytest -k body_above_the_limit` |
| Certificate valid, host unique | the `openssl` read and `--release` |
| Port 81 Tailscale-only | the two curls above |
| Ports 22/111/8096/52082 closed | `--ports` |
| `!shutdown` owner-only | `pytest tests/test_basic_cog.py -k shutdown` |
| 30-day retention | `pytest tests/test_retention.py` |
| Alerts and backup tested | `tools.backup_db verify` plus one unauthenticated call |
| No secret in logs | `pytest tests/test_redaction.py tests/test_logging_setup.py` |
| `make check` green, contract regenerated | `make check`, `git diff --exit-code -- web/src/lib/contract` |

Operator-only: certificate issued (NPM UI, record expiry), backup restored,
alert delivered, OAuth with a real bot, rotation rejected, cross-guild denial
with two accounts, `!shutdown` from both roles.

## Rollback

Delete the proxy host in the NPM UI (never the SQLite file), then the DNS
record. Lift a ban with `sudo fail2ban-client set <jail> unbanip <address>`.
