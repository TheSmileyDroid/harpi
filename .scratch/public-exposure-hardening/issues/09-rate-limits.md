# 09: Rate limits, quotas, body cap

**What to build:** The panel stays responsive under abuse. Authentication and the API are rate limited, request bodies are capped at 64 KB, searches and queues are limited per user, and live streams are capped per user and per guild.

**Blocked by:** 05. Edge network and egress deny, and 08. Proxy host, TLS, admin on Tailscale.

**Status:** ready-for-agent

- [ ] The proxy limits auth to 10 requests per minute per IP and the rest of the API to 60 per minute per IP.
- [ ] The app limits searches to 20 per minute per user and applies a queue token bucket.
- [ ] A request body above 64 KB receives 413.
- [ ] The app caps SSE at five connections per user and twenty per guild.
- [ ] Rate-limited responses use 429 with `Retry-After`.
- [ ] Tests cover the app limits, and integration checks cover the proxy limits.
- [ ] Demo: 30 searches receive 429, a 1 MB body receives 413, and the SSE cap holds.
