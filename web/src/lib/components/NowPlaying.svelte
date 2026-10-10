<script lang="ts">
  import { appStore } from "$lib/store";
  import { formatDuration, formatVolume } from "$lib/format";
  import Thumbnail from "./Thumbnail.svelte";

  const playback = $derived($appStore.playback);
  const connected = $derived($appStore.connection.connected);
  const track = $derived(playback?.current_music ?? null);
  const state = $derived(
    playback === null
      ? "Stopped"
      : playback.is_playing
        ? playback.is_paused
          ? "Paused"
          : "Playing"
        : "Stopped",
  );
</script>

<section
  class="hud-panel now-playing"
  class:is-playing={playback?.is_playing === true &&
    playback?.is_paused !== true}
  data-testid="playback-panel"
>
  <span class="panel-label">01 // Now Playing</span>
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
          <span class="data-label">State</span>
          <span class="data-value" data-testid="playback-state">{state}</span>
          <span class="data-label">Progress</span>
          <span class="data-value" data-testid="playback-progress">
            {formatDuration(playback.progress)} / {formatDuration(
              track?.duration,
            )}
          </span>
          <span class="data-label">Loop</span>
          <span class="data-value">{playback.loop_mode}</span>
          <span class="data-label">Volume</span>
          <span class="data-value">{formatVolume(playback.volume)}</span>
        </div>
      </div>
    </div>
  {/if}
</section>

<style>
  .now-playing__body {
    display: flex;
    align-items: flex-start;
    gap: 1rem;
  }

  :global(.now-playing__art) {
    flex: none;
    width: 6rem;
    height: 6rem;
    object-fit: cover;
    border: 1px solid var(--color-line);
    outline: 1px solid var(--color-line-strong);
    outline-offset: 2px;
  }

  .now-playing__meta {
    flex: 1;
    min-width: 0;
  }

  .now-playing__title {
    margin: 0 0 0.5rem;
    font-family: var(--font-display);
    font-weight: 600;
    font-size: 1.25rem;
    letter-spacing: 0.08em;
    color: var(--color-primary);
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
  }

  .now-playing__readouts {
    display: grid;
    grid-template-columns: max-content max-content;
    justify-content: start;
    gap: 0.25rem 0.75rem;
  }

  .now-playing__connect {
    margin-block-start: 0.75rem;
  }

  .now-playing__readouts :global(.data-label) {
    inline-size: auto;
  }

  @media (max-width: 30rem) {
    .now-playing__body {
      flex-direction: column;
    }

    :global(.now-playing__art) {
      width: 4rem;
      height: 4rem;
    }
  }
</style>
