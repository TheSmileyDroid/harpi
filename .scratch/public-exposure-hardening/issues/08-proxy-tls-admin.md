# 08: Proxy host, TLS, admin on Tailscale

**What to build:** The public hostname serves the panel over a valid certificate, with one proxy host, forced HTTPS, HSTS without `includeSubDomains`, and an admin interface reachable only through Tailscale.

**Blocked by:** 05. Edge network and egress deny.

**Status:** ready-for-agent

- [ ] Exactly one proxy host exists for `harpi.smileydroid.com.br`.
- [ ] The certificate is valid and issued by Let's Encrypt.
- [ ] Force SSL, HTTP/2, WebSocket upgrade, and HSTS without `includeSubDomains` are enabled.
- [ ] The admin interface on port 81 is not reachable from the public interface.
- [ ] The admin interface answers through Tailscale.
- [ ] fail2ban covers the proxy and SSH, and server tokens are off.
- [ ] Demo: valid certificate, public 81 timeout, Tailscale 81 response, HSTS header.
