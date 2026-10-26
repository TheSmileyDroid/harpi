# 04: Secret-free image and hardened runtime

**What to build:** The runtime image contains no secrets, runs as a non-root user with a read-only root, and uses a writable work directory for the cookie copy, yt-dlp scratch, and rotated logs. The master cookie is read-only.

**Blocked by:** None (can start immediately).

**Status:** ready-for-agent

- [ ] The build context excludes env files, cookies, logs, the database, `.git`, `.scratch`, tests, and caches.
- [ ] Image inspection finds no Discord token, YouTube cookie, or database.
- [ ] The master cookie is read-only, and the work directory is writable.
- [ ] The app boots with a read-only root and the prebuilt virtualenv entry point.
- [ ] The runtime is non-root, drops capabilities, sets `no-new-privileges`, and has PID and memory limits.
- [ ] The secret scan is clean, and the old token and cookie have been rotated.
- [ ] Demo: inspect the image, boot it read-only, and run the secret scanner.
