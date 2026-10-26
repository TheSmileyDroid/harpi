# 02: Secure login cookie and global logout

**What to build:** A signed-in viewer gets a host-scoped login cookie that scripts cannot read, that is never sent over plain HTTP, that expires after seven days, and that dies on every device when the viewer logs out. A forged Host header is rejected before routing.

**Blocked by:** 01. Allowlist admission and persisted guilds.

**Status:** ready-for-agent

- [ ] The cookie is named `__Host-harpi` with `Secure`, `HttpOnly`, `SameSite=Lax`, `Path=/`, and no `Domain`.
- [ ] The lifetime is seven days absolute, with no sliding renewal.
- [ ] `issued_at` and `login_epoch` are validated on every API request.
- [ ] Logout increments the epoch, and an old cookie receives 401.
- [ ] A forged `Host` header receives 400.
- [ ] Login clears the prior login state and emits a fresh cookie.
- [ ] HTTP-seam tests cover cookie flags, expiry, logout invalidation, and host rejection.
- [ ] Demo: inspect `Set-Cookie`, log out, replay the old cookie, and see 401.
