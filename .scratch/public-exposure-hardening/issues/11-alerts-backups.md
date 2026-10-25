# 11: Alerts and backups

**What to build:** The operator learns about attacks and can restore the registry after loss. Alerts go to a private Discord channel, and a daily local backup is tested.

**Blocked by:** 09. Rate limits, quotas, body cap, and 10. Logs, retention, DB permissions.

**Status:** ready-for-agent

- [ ] A Discord webhook alerts on 401, 403, 429, 5xx, SSE growth, and disk pressure.
- [ ] The webhook URL is a secret in the root-only environment.
- [ ] A daily local backup uses the SQLite backup API or a WAL checkpoint, not a raw copy of the live file.
- [ ] The restore test restores into a temporary database and compares row counts.
- [ ] The runbook covers alert response, backup restore, and secret rotation.
- [ ] Demo: trigger a 401 alert, restore a backup, and compare the registry counts.
