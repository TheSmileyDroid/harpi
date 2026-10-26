# 10: Logs, retention, DB permissions

**What to build:** Logs rotate and contain no secrets, the database is private, and old presence and connection data is deleted after 30 days.

**Blocked by:** None (can start immediately).

**Status:** ready-for-agent

- [ ] Loguru rotates at a bounded size, keeps a bounded number of files, and logs at INFO in production.
- [ ] URL, token, cookie, and authorization values are redacted before logging.
- [ ] yt-dlp runs quiet, without verbose request headers.
- [ ] The database file is mode 600.
- [ ] The retention job deletes viewers and connection events older than 30 days and keeps newer rows.
- [ ] Tests cover redaction and the retention boundary.
- [ ] Demo: rotate a log, grep for a token, and run the retention job against old and new rows.
