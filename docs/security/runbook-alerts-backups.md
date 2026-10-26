# Runbook: alerts, registry backups, and secret rotation

The operator learns about attacks from a private Discord channel and can
restore the panel registry after a loss. The webhook and the backup directory
are the only moving parts.

## Alerts

`PANEL_ALERT_WEBHOOK` holds the webhook URL. Keep it in the root-only `.env`
with mode 600. An unset or empty value turns alerts into a no-op, so the panel
runs without a webhook.

| Alert | Fires when | Threshold |
| --- | --- | --- |
| `401 unauthorized` | a request answers 401 | every source, coalesced for 60 s |
| `403 forbidden` | a request answers 403 | every source, coalesced for 60 s |
| `429 rate limited` | the application answers 429 | app-level limits only, coalesced for 60 s |
| `5xx server error` | a request answers 500 or above | every source, coalesced for 60 s |
| `SSE stream growth` | live streams cross the threshold | 15 concurrent streams |
| `disk pressure` | the data volume crosses the threshold | 85% used |

The dispatcher queues alerts on a bounded queue of 32 and one background
worker sends them. A full queue drops the alert and logs a warning; it never
blocks or fails the request. Repeated identical alerts within 60 seconds are
coalesced. The webhook URL never reaches a log line.

### Response by alert

- **401 or 403.** Read the `security event=access_denied` line in
  `security.log` for the user id, address, and time. Confirm the address is not
  a viewer behind a broken cookie. A sustained stream from one address is
  credential probing: block the address at the proxy and keep the alert on.
- **429.** A proxy `limit_req` rejection never reaches the application, so it
  does not raise this alert. Read `deploy/npm/harpi-advanced.conf` and the NPM
  access log for those; the alert covers the app-level search, queue, and
  stream limits. One viewer hitting search or
  queue limits is expected. Many addresses hitting the auth path means the
  proxy limit is doing its job; raise the limit only after confirming the
  traffic is legitimate.
- **5xx.** Read `harpi.log` for the traceback and the failing route. Restart
  the backend once if the process is unhealthy, then check the panel and the
  bot login line. A repeat means the fault is in the code or the data volume.
- **SSE stream growth.** Check the viewer list and the per-user and per-guild
  stream caps. Many tabs from one viewer is harmless; many users is a load
  event; one address opening streams in a loop is abuse.
- **Disk pressure.** Check `df -h` on the data volume. Prune rotated logs and
  old backups, then grow the volume. The alert stays silent until usage drops
  below the threshold and crosses it again.

### Webhook rotation

1. In the private Discord channel, open **Integrations**, delete the old
   webhook, and create a new one. Copy the URL once.
2. Replace `PANEL_ALERT_WEBHOOK` in the host `.env` and keep mode 600.
3. Recreate the backend so the new value enters the process:

   ```sh
   docker compose up -d --force-recreate backend
   ```

4. Trigger one alert with an unauthenticated API call and confirm the message
   reaches the channel:

   ```sh
   curl -sS -o /dev/null -w '%{http_code}\n' https://harpi.smileydroid.com.br/api/status
   ```

The Discord token and the YouTube cookie rotate through
[runbook-secret-rotation.md](runbook-secret-rotation.md). This runbook does not
repeat those steps.

## Backups

The app writes one backup at startup and one every 24 hours. The copy goes
through the SQLite backup API, so the live database keeps serving while the
file is written. Backups live under `HARPI_WORK_DIR/backups` (`/work/backups`
in the container), carry a UTC timestamp, are mode 600, and the newest seven
are kept.

Run a backup and a restore check by hand:

```sh
docker compose exec -w /app backend /app/.venv/bin/python -m tools.backup_db backup
docker compose exec -w /app backend /app/.venv/bin/python -m tools.backup_db verify
```

`backup` prints the target path and the `users`, `viewers`, and
`connection_events` counts. `verify` restores the newest backup into a
temporary database and compares those counts with the live registry. Exit code
1 means a mismatch or an unreadable backup. Name a specific file after
`verify` to check it instead of the newest one:

```sh
docker compose exec -w /app backend \
  /app/.venv/bin/python -m tools.backup_db verify \
  /work/backups/harpi-20261026T120000Z.db
```

### Restore after a loss

1. Run the restore check first. Stop while it fails.

   ```sh
   docker compose exec -w /app backend /app/.venv/bin/python -m tools.backup_db verify
   ```

2. Stop the backend so no process holds the database.

   ```sh
   docker compose stop backend
   ```

3. Copy the chosen backup over the live database and remove the old journal
   files. The `data/` directory is a host bind mount.

   ```sh
   docker compose cp backend:/work/backups/harpi-20261026T120000Z.db ./data/harpi.db
   rm -f data/harpi.db-wal data/harpi.db-shm
   chmod 600 data/harpi.db
   ```

4. Start the backend and confirm the panel lists the same users and presence.

   ```sh
   docker compose start backend
   docker compose logs --tail=20 backend
   ```

5. Sign in to the panel once, then run `verify` again. The new daily backup
   should carry the restored counts.

A restore keeps the webhook and every other secret untouched. The database
holds no secret, only user ids, names, selections, and connection events.

## Verification

```sh
docker compose exec -w /app backend /app/.venv/bin/python -m tools.backup_db verify
docker compose logs --tail=50 backend | grep -E "Panel storage|Registry backup"
```

Expected: the restore check passes and the log shows the storage path and no
backup failure. The alert path needs a real webhook: send an unauthenticated
API call and confirm the `401 unauthorized` message arrives.
