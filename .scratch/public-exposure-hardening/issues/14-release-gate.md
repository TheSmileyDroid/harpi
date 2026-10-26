# 14: Release gate verification

**What to build:** The release gate proves the public subdomain is safe to create. The checklist is complete, the container probes pass, the external scan shows only 80 and 443, and the normal gates are green.

**Blocked by:** 01, 02, 03, 04, 05, 06, 07, 08, 09, 10, 11, 12, and 13.

**Status:** ready-for-agent

- [ ] Every item in the release checklist is true.
- [ ] Unauthenticated API calls return 401, and the documentation endpoints return 404.
- [ ] The login cookie carries `__Host-`, `Secure`, `HttpOnly`, `SameSite=Lax`, and `Path=/`.
- [ ] The SSRF probe is blocked, and a normal YouTube URL still works.
- [ ] The external scan shows only 80 and 443 open.
- [ ] `make check` is green, and the contract is regenerated.
- [ ] No DNS record or proxy host was created before the gate passed.
- [ ] Demo: run the checklist and the container probes against the release commit.
