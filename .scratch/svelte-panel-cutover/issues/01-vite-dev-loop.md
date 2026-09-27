# 01: Vite dev loop

**What to build:** One command starts the whole development loop: the frontend dev server with hot module reload, the backend with its reload behavior, and the CSS build. Editing a frontend module updates the browser without a manual refresh, and a shell-level change reloads the page through the backend's SSE channel. Existing repo gates stay green. This lands on main before the cutover branch opens.

**Blocked by:** None (can start immediately)

**Status:** ready-for-agent

- [x] A single command boots the frontend dev server, the backend, and the CSS build
- [x] Editing a frontend module updates the browser without a manual refresh
- [x] A shell-level change triggers a browser reload through the SSE signal
- [x] `make check` still exits 0 on main
