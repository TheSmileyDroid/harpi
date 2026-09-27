# 03: API foundation

**What to build:** The app answers a JSON API behind a session boundary and exposes a live event stream. Signing in exchanges a token from the environment for a session cookie, unauthenticated calls are rejected server-side, and bot status arrives as SSE events that reconnect after a drop. Everything here is verifiable without a browser.

**Blocked by:** 02

**Status:** ready-for-agent

- [ ] Token exchange issues an HttpOnly session cookie; missing or bad tokens are rejected
- [ ] Every non-public endpoint returns 401 without a valid session
- [ ] The status endpoint returns a documented JSON shape
- [ ] The SSE stream emits status events and recovers from a dropped connection without duplicating state
- [ ] pytest covers the contract, auth rejection, and the event shape at the app's HTTP seam
- [ ] The API binds to localhost by default
