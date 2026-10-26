# 05: Edge network and egress deny

**What to build:** The app is reachable only through the proxy on the `harpi-edge` network. No host port is published, the proxy reaches the app by service name, and the container cannot reach private networks.

**Blocked by:** 04. Secret-free image and hardened runtime.

**Status:** ready-for-agent

- [ ] Compose publishes no host port, and NPM and the app join `harpi-edge`.
- [ ] The proxy reaches `harpi-backend:8000` by service name.
- [ ] Only `data/`, the work directory, and the read-only cookie are mounted.
- [ ] The container cannot reach loopback, RFC1918, link-local, or the metadata address.
- [ ] YouTube and Discord egress still works.
- [ ] `ss` on the host shows no 8000 listener.
- [ ] Demo: host port scan, proxy request, and a private-address probe from inside the container.
