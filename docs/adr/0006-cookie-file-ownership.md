# yt-dlp works from a copy of the cookie file

The YouTube session cookie set at the repo root (`cookies.txt`) is logged-in state that is hard to recreate and impossible to regenerate bit-for-bit. yt-dlp can rewrite a cookie file it is given: it refreshes session cookies from server responses and saves the jar on close, which is how a working `cookies.txt` was previously corrupted into a broken one. Harpi now treats the master file as read-only input. Each process copies it to `cookies.work.txt` in the writable work directory (`HARPI_WORK_DIR`, `data/work` by default) and points yt-dlp at the copy, so yt-dlp can refresh and rewrite freely without touching the master. When the copy differs from the master at process exit, it is saved as `cookie-backups/cookies.<timestamp>.txt` and the master is left as it was. The startup log records the master's sha256 so a change is detectable across runs.

## Considered options

- **Back up the master before each run and let yt-dlp write it**: rejected. A backup only helps recovery; it still lets a bad write become the live file that the next run reads.
- **Mount the master read-only and let yt-dlp write it**: rejected. The mount is now read-only as defense in depth, but it is not the only control: the working copy absorbs every write, so a missing or misconfigured mount does not corrupt the master.
- **Disable cookie persistence entirely**: rejected. Refreshed cookies are worth keeping; the versioned backups retain them without risking the master.

## Consequences

- The master `cookies.txt` is never written by Harpi; only backups under `cookie-backups/` in the work directory accumulate.
- `cookiefile` is an absolute working-copy path under the work directory, independent of the process working directory.
- The container mounts the master read-only and the work directory writable, so the copy is the only cookie file the runtime can change.
- An edited cookie is recoverable: the backup holds exactly what yt-dlp produced.
