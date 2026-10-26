# 07: Security headers, CSP, docs off

**What to build:** Every response carries the security headers, the panel has a content security policy, and the API schema and documentation UIs are not reachable in production.

**Blocked by:** None (can start immediately).

**Status:** ready-for-agent

- [ ] Responses carry HSTS, `X-Content-Type-Options`, `Referrer-Policy`, `Permissions-Policy`, COOP, CORP, `X-Frame-Options`, and CSP.
- [ ] The first CSP allows the app origin, the inline SvelteKit bootstrap, and the Google Fonts origins.
- [ ] The follow-up moves fonts to the app origin and uses a build-time hash for the inline script.
- [ ] `/openapi.json`, `/docs`, `/redocs`, and `/scalar` return 404 in production.
- [ ] The `Server` header is hidden.
- [ ] Tests cover the header set and the disabled documentation endpoints.
- [ ] Demo: `curl -I` shows the headers, and the documentation paths return 404.
