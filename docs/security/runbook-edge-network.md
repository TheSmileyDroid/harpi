# Runbook: edge network and egress deny

Harpi publishes no host port. Nginx Proxy Manager reaches it as `harpi-backend:8000` over the external `harpi-edge` network, and `DOCKER-USER` rules deny the container egress to private, link-local, and metadata addresses. Public egress to YouTube and Discord stays open.

Run every step on the Docker host as a user in the `docker` group; the egress steps need root.

## 1. Create the network

```sh
docker network inspect harpi-edge >/dev/null 2>&1 || docker network create harpi-edge
```

The network is external to Compose, so `docker compose down` never removes it.

## 2. Attach Nginx Proxy Manager

Add `harpi-edge` to the NPM service in `/home/opc/external/nginx/docker-compose.yml`:

```yaml
services:
  app:
    networks:
      - npm_proxy
      - harpi-edge

networks:
  npm_proxy:
    external: true
    name: "robsons"
  harpi-edge:
    external: true
```

Then recreate the proxy:

```sh
cd /home/opc/external/nginx
docker compose up -d app
```

`docker network connect harpi-edge nginx-app-1` attaches the running container without the file edit, but the attachment is lost on the next recreate. Recreating NPM briefly drops every site the proxy serves.

## 3. Start Harpi

```sh
cd /path/to/harpi
docker compose up -d backend
```

Compose fails with `network harpi-edge declared as external, but could not be found` when step 1 was skipped.

## 4. Apply the egress deny

```sh
sudo ./deploy/egress-deny.sh print
sudo ./deploy/egress-deny.sh apply
```

`print` renders the rules for the container's current addresses and changes nothing. `apply` inserts each missing rule and reports how many it added; a second run adds none. It exits non-zero when the container has no address or the chain is absent.

For every container source address `S`, the IPv4 rules are:

```sh
iptables -I DOCKER-USER -s S -d 127.0.0.0/8     -m comment --comment harpi-egress-deny -j DROP
iptables -I DOCKER-USER -s S -d 10.0.0.0/8      -m comment --comment harpi-egress-deny -j DROP
iptables -I DOCKER-USER -s S -d 172.16.0.0/12   -m comment --comment harpi-egress-deny -j DROP
iptables -I DOCKER-USER -s S -d 192.168.0.0/16  -m comment --comment harpi-egress-deny -j DROP
iptables -I DOCKER-USER -s S -d 169.254.0.0/16  -m comment --comment harpi-egress-deny -j DROP
iptables -I DOCKER-USER -s S -d 224.0.0.0/4     -m comment --comment harpi-egress-deny -j DROP
```

`169.254.0.0/16` covers the cloud metadata address `169.254.169.254`. When the container has an IPv6 address, `ip6tables` gets the same rules for `::1/128`, `fc00::/7`, `fe80::/10`, and `ff00::/8`.

Re-run `remove` then `apply` after the container is recreated, because the rules match the address it had when they were installed.

## 5. Verify the host port is gone

```sh
sudo ss -tlnp | grep -E ':(80|443|8000)\b'
docker inspect harpi-backend --format '{{json .HostConfig.PortBindings}}'
```

Expected: only 80 and 443 listen, and the port bindings print `{}`. The app still listens on `0.0.0.0:8000` inside its own network namespace, where only `harpi-edge` reaches it.

## 6. Verify the proxy reaches the app by name

```sh
docker network inspect harpi-edge --format '{{range .Containers}}{{.Name}} {{.IPv4Address}}{{"\n"}}{{end}}'
docker run --rm --network harpi-edge alpine:3.20 \
  wget -qO- -T 3 http://harpi-backend:8000/ | head -c 120
```

Expected: `harpi-backend` and `nginx-app-1` on the network, and the panel HTML from the probe. The NPM proxy host forwards to hostname `harpi-backend`, port `8000`, scheme `http`, with WebSocket support on.

## 7. Probe private addresses from inside the container

```sh
docker exec harpi-backend sh -c 'curl -sS --max-time 3 http://169.254.169.254/; echo "metadata exit=$?"'
docker exec harpi-backend sh -c 'curl -sS --max-time 3 http://10.0.0.1/; echo "rfc1918 exit=$?"'
```

Expected: both commands print `exit=28`, the curl timeout. A connection refused or an HTTP response means the packet left the container and the rule set is incomplete.

Confirm public egress still works:

```sh
docker exec harpi-backend sh -c 'curl -sS -o /dev/null -w "youtube=%{http_code}\n" --max-time 10 https://www.youtube.com/'
docker exec harpi-backend sh -c 'curl -sS -o /dev/null -w "discord=%{http_code}\n" --max-time 10 https://discord.com/api/v10/gateway'
```

Expected: `youtube=200` or `301`, and `discord=200`.

## 8. Remove the rules

```sh
sudo ./deploy/egress-deny.sh remove
```

`remove` deletes every `DOCKER-USER` rule carrying the `harpi-egress-deny` comment, including rules left by a previous container address. It does not need the container to exist.

Without the script:

```sh
iptables -S DOCKER-USER | grep harpi-egress-deny | sed 's/^-A/-D/' | xargs -r -L1 iptables
```

Flushing `DOCKER-USER` (`iptables -F DOCKER-USER`) also removes rules owned by other workloads on the host; delete only the tagged rules.

## Limits

- `DOCKER-USER` sees forwarded traffic. Packets the container sends to an address owned by the host, such as the bridge gateway, the host LAN address, or the Tailscale address, are delivered through `INPUT` and stay outside these rules. Close those on the host firewall when the threat model requires it.
- The rules do not survive a reboot or a Docker daemon restart. Re-apply them after either, or wrap `apply` in a systemd unit.
- DNS must not resolve through a blocked range. The host uses MagicDNS at `100.100.100.100`, which these rules allow. If `docker exec harpi-backend cat /etc/resolv.conf` shows an RFC1918 resolver, add an `ACCEPT` for that resolver above the `DROP` rules before deploying.
