<script lang="ts">
  import { appStore } from "$lib/store";
  import { formatDuration, formatVolume } from "$lib/format";
  import Thumbnail from "./Thumbnail.svelte";

  const playback = $derived($appStore.playback);
  const botOnline = $derived($appStore.bot.online);
  const connected = $derived($appStore.connection.connected);
  const track = $derived(playback?.current_music ?? null);
  const playbackState = $derived(
    playback === null
      ? "Stopped"
      : playback.is_playing
        ? playback.is_paused
          ? "Paused"
          : "Playing"
        : "Stopped",
  );
  const isPaused = $derived(playback?.is_paused === true);
  const lampMode = $derived(
    playback?.is_playing !== true
      ? null
      : isPaused
        ? "paused"
        : botOnline
          ? "live"
          : null,
  );
  const lockKey = $derived(
    playback?.is_playing === true && !isPaused && botOnline
      ? `${track?.url ?? ""}|${playbackState}`
      : null,
  );
  let lockId = $state(0);
  let lastLockKey: string | null = null;

  $effect(() => {
    if (lockKey === lastLockKey) return;
    lastLockKey = lockKey;
    if (lockKey !== null) lockId += 1;
  });
</script>

<section
  class="hud-panel now-playing"
  class:is-playing={playback?.is_playing === true &&
    playback?.is_paused !== true &&
    botOnline}
  class:is-paused={playback?.is_playing === true &&
    playback?.is_paused === true}
  data-testid="playback-panel"
>
  {#if lockId > 0}
    {#key lockId}<span class="now-playing__lock" aria-hidden="true"
      ></span>{/key}
  {/if}
  {#if lampMode !== null}
    {#key lockId}<span
        class="now-playing__lamp"
        class:is-paused={lampMode === "paused"}
        aria-hidden="true"
      ></span>{/key}
  {/if}
  <span class="panel-label">
    Now Playing
    {#if !botOnline}<span class="panel-stale">bot offline</span>{/if}
  </span>
  {#if playback === null}
    <p class="data-value is-empty" data-testid="playback-empty">
      {connected ? "Voice link up, no session" : "No active session"}
    </p>
    <button
      type="button"
      class="hud-btn now-playing__connect"
      onclick={(event) => {
        event.stopPropagation();
        appStore.openOutput();
      }}
      data-testid="connect-output"
    >
      {connected ? "Reconnect output" : "Connect output to begin"}
    </button>
  {:else}
    <div class="now-playing__body">
      <Thumbnail
        src={track?.thumbnail ?? ""}
        alt={track?.title ?? "Now playing"}
        className="now-playing__art"
        size={96}
      />
      <div class="now-playing__meta">
        <p class="now-playing__title" data-testid="now-playing">
          {track?.title ?? "Nothing playing"}
        </p>
        <div class="now-playing__readouts">
          <span class="now-playing__cell">
            <span class="data-label">State</span>
            <span class="data-value" data-testid="playback-state"
              >{playbackState}</span
            >
          </span>
          <span class="now-playing__cell">
            <span class="data-label">Progress</span>
            <span class="data-value" data-testid="playback-progress">
              {formatDuration(playback.progress)} / {formatDuration(
                track?.duration,
              )}
            </span>
          </span>
          <span class="now-playing__cell">
            <span class="data-label">Loop</span>
            <span class="data-value">{playback.loop_mode}</span>
          </span>
          <span class="now-playing__cell">
            <span class="data-label">Volume</span>
            <span class="data-value">{formatVolume(playback.volume)}</span>
          </span>
        </div>
      </div>
    </div>
  {/if}
</section>

<style>
  .now-playing__body {
    display: grid;
    grid-template-columns: auto minmax(0, 1fr);
    gap: 1rem;
    align-items: start;
  }

  :global(.now-playing__art) {
    flex: none;
    width: 6rem;
    height: 6rem;
    object-fit: cover;
    border: 1px solid var(--line-strong);
    border-block-end-width: 2px;
  }

  .now-playing__meta {
    display: flex;
    flex-direction: column;
    gap: 0.85rem;
    min-width: 0;
  }

  .now-playing__title {
    margin: 0;
    font-family: var(--font-display);
    font-weight: 400;
    font-size: 1.05rem;
    letter-spacing: 0.05em;
    color: var(--ink);
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
  }

  .now-playing__readouts {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(7rem, 1fr));
    gap: 0.5rem 1rem;
  }

  .now-playing__cell {
    display: flex;
    flex-direction: column;
    gap: 0.15rem;
    border-top: 1px solid var(--line);
    padding-block-start: 0.35rem;
  }

  .now-playing__cell .data-label {
    inline-size: auto;
  }

  .now-playing__connect {
    margin-block-start: 0.85rem;
  }

  .panel-stale {
    margin-inline-start: 0.4rem;
    padding: 0.05rem 0.35rem;
    border: 1px solid var(--alert-dim);
    color: var(--alert);
    letter-spacing: 0.14em;
  }

  .now-playing__lamp {
    position: absolute;
    inset-block-start: -1px;
    inset-inline-start: -1px;
    inline-size: 0.7rem;
    block-size: 0.7rem;
    background: var(--lamp);
    transition: background-color var(--motion-settle) ease-out;
  }

  .now-playing__lamp.is-paused {
    background: var(--lamp-dim);
  }

  .now-playing__lock {
    position: absolute;
    inset-block-start: 0;
    inset-inline: 0;
    block-size: 0.35rem;
    transform-origin: left center;
    background: var(--lamp);
    pointer-events: none;
  }

  @media (prefers-reduced-motion: no-preference) {
    .now-playing__lamp {
      animation: lamp-lock 640ms steps(1, end) backwards;
    }

    .now-playing__lock {
      animation: lock-sweep 620ms var(--ease-arrive) forwards;
    }
  }

  @media (prefers-reduced-motion: reduce) {
    .now-playing__lock {
      display: none;
    }
  }

  @media (max-width: 30rem) {
    .now-playing__body {
      grid-template-columns: auto minmax(0, 1fr);
    }

    :global(.now-playing__art) {
      width: 4rem;
      height: 4rem;
    }

    .now-playing__readouts {
      grid-template-columns: repeat(2, minmax(0, 1fr));
    }
  }
</style>
