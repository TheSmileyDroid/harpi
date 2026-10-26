# Runbook: rotate the Discord token and the YouTube cookie

The Discord bot token and the master YouTube cookie are replaced only by rotation. Rotate both after the secret-free image is built and scanned, because older images on the host still contain the previous values.

## Discord bot token

1. Open the Discord Developer Portal, select the Harpi application, open **Bot**, and press **Reset Token**. Copy the new value once.
2. Replace `DISCORD_TOKEN` in the host `.env`. Keep the file mode at 600.
3. Recreate the container so the new value enters the process environment:

   ```sh
   docker compose up -d --force-recreate backend
   ```

4. Check `docker compose logs backend` for a bot login line and confirm the bot shows as online in Discord. Sign in to the panel once to confirm the OAuth flow still works.

The reset invalidates the old token immediately. A copy of the old token in a previous image, a shell history, or a backup answers `401 Unauthorized` from the Discord API.

## YouTube master cookie

The container reads `/app/cookies.txt` once at import and copies it into the writable work directory. The mount is read-only, so yt-dlp never writes the master.

1. Sign in to YouTube in a browser, export the cookies in Netscape format, and keep the file off the repository and off any shared path.
2. Replace the host `cookies.txt`, then set the mode:

   ```sh
   chmod 600 cookies.txt
   ```

3. Restart the container so the copy is refreshed:

   ```sh
   docker compose restart backend
   ```

4. Search and play one track from the panel. The startup log prints `cookie master sha256=<digest>`; compare it with `sha256sum cookies.txt` on the host.

Edits yt-dlp makes to its copy land in `/work/cookie-backups/` on the `harpi-work` volume. The master stays as uploaded.

## Verification after either rotation

```sh
docker compose logs --tail=50 backend
docker compose exec backend touch /app/cookies.txt
docker compose exec backend test -w /work
```

The first command shows the bot login and the cookie digest. The second must fail with `Read-only file system`. The third succeeds only while the work directory is writable.

## Image check

The old image carries the previous token and cookie. Remove it after the new build passes the secret scan:

```sh
docker run --rm --entrypoint sh IMAGE -c 'ls /app/.env /app/cookies.txt /app/data; find /app -maxdepth 1 -name "*.log"'
gitleaks detect
trivy image --scanners secret IMAGE
```

The `ls` and `find` commands must print nothing but missing-path errors. The scanners must report no findings before the image is tagged for deployment.
