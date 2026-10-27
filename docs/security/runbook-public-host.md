# Runbook: public host, certificate, and admin lockdown

This is the order that puts `harpi.smileydroid.com.br` on the internet. Nothing here has been run. The files it applies live in `deploy/`, and the gate it obeys is in [public-exposure-plan.md](public-exposure-plan.md#gate-de-liberação).

No DNS record and no proxy host may exist before every gate box is true. A record or a host created early makes a half-hardened panel reachable.

## 1. Confirm the gate

Read the gate list in [public-exposure-plan.md](public-exposure-plan.md#gate-de-liberação) and check every box. The deployment items a later step assumes:

```sh
docker inspect harpi-backend --format '{{json .HostConfig.PortBindings}}'
docker network inspect harpi-edge --format '{{range .Containers}}{{.Name}} {{end}}'
sudo ss -tlnp | grep -E ':(80|443|8000)\b'
```

Expected: `{}`, `harpi-backend nginx-app-1`, and only 80 and 443 listening. The edge and egress steps are in [runbook-edge-network.md](runbook-edge-network.md).

Stop here while any box is empty.

## 2. Create the DNS record at Registro.br

Add one record at Registro.br:

| Type | Name | Value | TTL |
| --- | --- | --- | --- |
| A | `harpi` | the host public IPv4 | 3600 |

Add an `AAAA` record only when the host answers on IPv6 end to end. Do not add a wildcard. Cloudflare stays out of the path.

```sh
dig +short A harpi.smileydroid.com.br
```

Expected: one address, the same one the host uses. Wait for the answer before the certificate step, because Let's Encrypt validates over port 80.

## 3. Create the proxy host

The script prints every request and body it would send. It writes nothing without `--apply`.

```sh
deploy/npm-proxy-host.sh
```

Then apply, with the NPM admin credentials in the environment. The admin answers only on Tailscale, so the default base URL is `http://100.106.27.40:81`.

```sh
NPM_IDENTITY=you@example.com NPM_PASSWORD='...' deploy/npm-proxy-host.sh --apply
```

It creates one host for `harpi.smileydroid.com.br` forwarding to `harpi-backend:8000` over `http`, with `Block Common Exploits` on, caching off, WebSocket upgrade on, and the Advanced tab set from `deploy/npm/harpi-advanced.conf`:

```nginx
server_tokens off;
proxy_buffering off;
proxy_read_timeout 1h;
proxy_send_timeout 1h;

client_max_body_size 64k;
limit_req_status 429;

location /api/auth/ {
	limit_req zone=harpi_auth burst=3 nodelay;
	proxy_pass http://harpi-backend:8000;
	proxy_http_version 1.1;
	proxy_set_header Host $host;
	proxy_set_header X-Forwarded-Scheme $scheme;
	proxy_set_header X-Forwarded-Proto $scheme;
	proxy_set_header X-Forwarded-For $remote_addr;
	proxy_set_header X-Real-IP $remote_addr;
}

location /api/ {
	limit_req zone=harpi_api burst=10 nodelay;
	proxy_pass http://harpi-backend:8000;
	proxy_http_version 1.1;
	proxy_set_header Host $host;
	proxy_set_header X-Forwarded-Scheme $scheme;
	proxy_set_header X-Forwarded-Proto $scheme;
	proxy_set_header X-Forwarded-For $remote_addr;
	proxy_set_header X-Real-IP $remote_addr;
}
```

`proxy_set_header Host $host` keeps the panel's trusted-host check on the public name; without it the app sees `harpi-backend:8000` and answers 400. Both locations repeat the proxy headers because NPM's own `location /` does not share them with a sibling location.

`proxy_buffering off` keeps the `/api/events` SSE stream live. The app does not send `X-Accel-Buffering`, and nginx buffers event streams by default.

The snippet hides `Server` with `more_clear_headers`, which needs the
headers-more module that NPM bundles. If nginx refuses to start after the
snippet, check that module before removing the line.

The Advanced tab is server context, so the zones and the status map cannot live there. They belong to the custom http context, in `deploy/npm/harpi-rate-limits-http.conf`:

```nginx
limit_req_zone $binary_remote_addr zone=harpi_auth:1m rate=10r/m;
limit_req_zone $binary_remote_addr zone=harpi_api:1m rate=60r/m;

map $status $harpi_retry_after {
	429 "30";
	default "";
}
```

Install it as `http_top.conf`, not `http.conf`. NPM includes `proxy_host/*.conf` before `http.conf`, so a `map` or zone defined in `http.conf` is still unknown when the host config is parsed:

```sh
install -m 644 deploy/npm/harpi-rate-limits-http.conf /home/opc/external/nginx/data/nginx/custom/http_top.conf
docker exec nginx-app-1 nginx -t
docker exec nginx-app-1 nginx -s reload
```

Expected: `syntax is ok` and `test is successful`. A stock NPM ships neither file; if `http_top.conf` already has content, append these lines instead of overwriting. Without them, `nginx -t` fails with `unknown "harpi_retry_after" variable` or `unknown limit_req zone "harpi_api"`.

| Zone | Rate | Burst | Applied to |
| --- | --- | --- | --- |
| `harpi_auth` | 10 requests per minute per IP | 3 | `/api/auth/` |
| `harpi_api` | 60 requests per minute per IP | 10 | the rest of `/api/` |

`client_max_body_size 64k` rejects a larger body at the proxy. The app applies the same cap itself, so a direct container request gets the JSON envelope.

The host exists without a certificate at this point, so NPM stores it with forced HTTPS, HTTP/2, and HSTS off. NPM 2.12.6 clears those flags whenever no certificate is attached, and a request that carries them anyway is silently normalized.

The script aborts when more than one host claims the hostname. Delete the extras in the NPM UI, never in the SQLite file.

## 4. Issue the certificate

```sh
NPM_IDENTITY=you@example.com NPM_PASSWORD='...' deploy/npm-proxy-host.sh --apply --certificate new
```

NPM runs the Let's Encrypt HTTP-01 challenge over port 80 and then the script writes the host again with the certificate attached and forced HTTPS, HTTP/2, and HSTS on. HSTS is emitted without `includeSubDomains`; NPM adds the `preload` token, which stays inert unless the domain is submitted to hstspreload.org.

Re-running the command reuses the certificate already attached to the host instead of issuing another one. To attach a certificate created in the NPM UI instead:

```sh
NPM_IDENTITY=you@example.com NPM_PASSWORD='...' deploy/npm-proxy-host.sh --apply --certificate <id>
```

## 5. Move the admin interface to Tailscale

The NPM admin port must answer on the Tailscale address and stay silent on the public one. Change the port mapping in `/home/opc/external/nginx/docker-compose.yml`:

```yaml
services:
  app:
    ports:
      - '80:80'
      - '100.106.27.40:81:81'
      - '443:443'
```

Then recreate the proxy, which drops every site it serves for a few seconds:

```sh
cd /home/opc/external/nginx
docker compose up -d app
```

The host firewall alternative is a rule that accepts 81 on `tailscale0` and drops it on the public interface. Binding the published port to the Tailscale address is the smaller change.

Check it:

```sh
deploy/check-admin-exposure.sh
```

Expected: the public address does not answer, the Tailscale address answers, and the script exits 0. It fails when `http://PUBLIC_IP:81` returns any status. Pass `--public-ip` and `--tailscale-ip` when detection picks the wrong address.

## 6. Install fail2ban

NPM writes the admin access log to `/dev/null` in the image, so failed admin logins leave no trace. `deploy/npm/admin-production.conf` is the NPM 2.12.6 admin server block with `access_log /data/logs/admin_access.log standard;` and `server_tokens off;`. Copy it into `/home/opc/external/nginx/` and mount it read-write in the NPM compose service:

```yaml
services:
  app:
    volumes:
      - ./admin-production.conf:/etc/nginx/conf.d/production.conf
```

The mount must be writable. NPM's IPv6 prepare script edits every file in `conf.d`, and a `:ro` mount aborts the container start with `Read-only file system`. The file is tied to NPM 2.12.6: after an image upgrade, diff it against `/etc/nginx/conf.d/production.conf` in the new image and re-apply the two changed lines.

The NPM logs live under `/home/opc`, and the fail2ban service cannot read that path in its unit context. Bind-mount the log directory to `/var/log/npm` and persist it:

```sh
sudo mkdir -p /var/log/npm
sudo mount --bind /home/opc/external/nginx/data/logs /var/log/npm
grep -q '/var/log/npm' /etc/fstab \
  || echo '/home/opc/external/nginx/data/logs /var/log/npm none bind 0 0' | sudo tee -a /etc/fstab
sudo semanage fcontext -a -t var_log_t '/home/opc/external/nginx/data/logs(/.*)?'
sudo restorecon -R /home/opc/external/nginx/data/logs
```

Then install the filters, the action, and the jails:

```sh
sudo deploy/fail2ban/install.sh
```

The jail file enables three jails:

| Jail | Filter | Log |
| --- | --- | --- |
| `npm-admin-auth` | failed `POST /api/tokens` with 401 or 403 | `/var/log/npm/admin_access.log` |
| `harpi-auth` | failed `/api/auth/` requests with 401 or 403 | `/var/log/npm/proxy-host-*_access.log` |
| `sshd` | failed SSH logins | the distribution default |

Both proxy jails ban through `npm-docker-user`, which inserts a `DROP` into `DOCKER-USER`. The stock `iptables-multiport` action writes to `INPUT`, which never sees traffic to a Docker-published port. A ban drops every forwarded packet from that address, not only port 81, and it writes `iptables` rules only; a peer that reaches the panel over IPv6 needs an `ip6tables` action.

The installer refuses to run when the admin log or the proxy host log is missing, and it runs `fail2ban-client -t` before reloading. Confirm afterwards:

```sh
sudo fail2ban-client status npm-admin-auth
sudo fail2ban-client status harpi-auth
sudo fail2ban-client status sshd
```

Expected: each jail lists `Currently banned` and `Total banned`.

## 7. Verify

```sh
deploy/verify-proxy.sh
```

It reads and changes nothing. Each check prints `PASS` or `FAIL`, and the script exits non-zero when any check fails:

| Check | Expected |
| --- | --- |
| certificate | issued by Let's Encrypt, valid for at least 14 days |
| forced HTTPS | plain HTTP answers 301 or 308 to `https://harpi.smileydroid.com.br` |
| HSTS | `Strict-Transport-Security` with `max-age`, no `includeSubDomains` |
| HTTP/2 | the HTTPS response is HTTP/2 |
| WebSocket | the upgrade request reaches the app, which answers 400 because it has no socket route |
| server tokens | no `Server: nginx/<version>` |
| admin port 81 | public address silent, Tailscale address answers |
| single host | exactly one host claims the hostname |

The single host check uses the NPM API when `NPM_TOKEN` or `NPM_IDENTITY` and `NPM_PASSWORD` are set, and otherwise counts the rendered configs in the `nginx-app-1` container.

The WebSocket check sends a handshake to `/`. A proxy that strips the upgrade headers returns 200 with the panel HTML; one that forwards them reaches the app, which answers 400.

The proxy rate limits have their own read-only check:

```sh
deploy/check-rate-limits.sh
```

It sends GET bursts to `/api/auth/discord` and `/api/session` and fails when a burst never receives `429`. Each burst stops at the first limited request, and the calling address stays rate limited for up to a minute afterwards. Pass `--url`, `--auth-limit`, and the other flags when the deployed values differ from the defaults.

## 8. Record the result

Append the verification output, the certificate expiry, and the date to `.scratch/public-exposure-hardening/issues/08-proxy-tls-admin.md`. Tick a gate box in [public-exposure-plan.md](public-exposure-plan.md) only when its own evidence exists.

Do not tick the DNS or proxy host boxes for this ticket: they describe the live state after this runbook, not the delivered files.

## Rollback

Delete the proxy host in the NPM UI. Do not edit `/home/opc/external/nginx/data/database.sqlite`, and do not delete the certificate while the host still points at it. Remove the DNS record at Registro.br last, after the host is gone.

To stop the bans without removing the jails:

```sh
sudo fail2ban-client set npm-admin-auth unbanip <address>
sudo fail2ban-client set harpi-auth unbanip <address>
```
