# yt-dlp works from a copy of the cookie file

The YouTube session cookie set at the repo root (`cookies.txt`) is logged-in state that is hard to recreate and impossible to regenerate bit-for-bit. yt-dlp can rewrite a cookie file it is given: it refreshes session cookies from server responses and saves the jar on close, which is how a working `cookies.txt` was previously corrupted into a broken one. Harpi now treats the master file as read-only input. Each process copies it to `.scratch/ytdl-debug/cookies.work.txt` and points yt-dlp at the copy, so yt-dlp can refresh and rewrite freely without touching the master. When the copy differs from the master at process exit, it is saved as `cookie-backups/cookies.<timestamp>.txt` and the master is left as it was. The startup log records the master's sha256 so a change is detectable across runs.

## Considered options

- **Back up the master before each run and let yt-dlp write it**: rejected. A backup only helps recovery; it still lets a bad write become the live file that the next run reads.
- **Mount the master read-only**: rejected. It needs filesystem or unit privileges and produces a hard failure when yt-dlp tries to save, instead of a working copy that absorbs the write.
- **Disable cookie persistence entirely**: rejected. Refreshed cookies are worth keeping; the versioned backups retain them without risking the master.

## Consequences

- The master `cookies.txt` is never written by Harpi; only backups under `.scratch/ytdl-debug/cookie-backups/` accumulate.
- `cookiefile` is an absolute working-copy path derived from the source tree, independent of the process working directory.
- An edited cookie is recoverable: the backup holds exactly what yt-dlp produced.
