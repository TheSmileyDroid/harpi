# Resolve YouTube JS runtimes by path, not PATH

YouTube's player requires an external JavaScript engine (deno, node, bun, or quickjs) to solve its signature and PO-token challenges; yt-dlp runs the engine via `js_runtimes`, and without one most streams are rejected as unplayable. The original detection used `shutil.which`, which reads `PATH`. Harpi runs as a systemd user service whose `PATH` is `/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin` and therefore contains none of the per-user install directories where the runtimes actually live (`~/.deno/bin`, `~/.bun/bin`, an nvm-style node directory). The bot silently extracted with no JS solver for days while the test suite passed, because the tests ran from an interactive shell whose `PATH` did have them. Detection now resolves each runtime to an absolute path, checking `PATH` first and then `HARPI_JS_RUNTIME_DIRS` followed by the default directories, and passes that path to yt-dlp as `{"path": <absolute>}`. Absolute paths are used because the environment the process inherits is not the environment the code assumes, and a silent degradation is worse than a wrong path.

## Considered options

- **Set `PATH` in the systemd unit only**: kept as a second layer, not the fix. It repairs this deployment and nothing else, and the next launch path (container, another host, a manual run) reintroduces the fault.
- **Hardcode the node install path (`~/.local/share/pi-node/*/bin`) in the repo**: rejected. It is one machine's layout; the configurable `HARPI_JS_RUNTIME_DIRS` covers it without baking a version into the source.
- **Fail startup when no runtime is found**: rejected for now. The warning stays a warning so a cookie-only degraded mode still serves whatever YouTube allows.

## Consequences

- `HARPI_JS_RUNTIME_DIRS` is a path-separated prepend list; unset, the defaults `~/.deno/bin`, `~/.bun/bin`, `~/.local/bin`, and `/usr/local/bin` still recover deno and bun.
- Startup logs the resolved runtime and its absolute path, so a missing solver is visible in one line.
- The deployment's systemd unit (in the host's systemd user config, outside this repo) also exports `PATH` with the runtime directories, so the deployment is not carried by the code alone.
