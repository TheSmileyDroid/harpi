<script lang="ts">
  import { appStore } from "$lib/store";
  import { formatDuration, formatVolume } from "$lib/format";
  import {
    layersCountLabel,
    loopModeLabel,
    playbackStateLabel,
  } from "$lib/music";
  import { positionSeconds } from "$lib/playback-clock";
  import Readout from "./Readout.svelte";
  import Thumbnail from "./Thumbnail.svelte";

  const playback = $derived($appStore.playback);
  const botOnline = $derived($appStore.bot.online);
  const connected = $derived($appStore.connection.connected);
  const track = $derived(playback?.current_music ?? null);
  const layers = $derived(playback?.layers ?? []);
  const duration = $derived(track?.duration ?? 0);
  const sourceLine = $derived(
    [track?.uploader, duration > 0 ? formatDuration(duration) : ""]
      .filter(Boolean)
      .join(" · "),
  );
  const playbackState = $derived(
    playbackStateLabel({
      hasPlayback: playback !== null,
      hasTrack: track !== null,
      isPlaying: playback?.is_playing ?? false,
      isPaused: playback?.is_paused ?? false,
    }),
  );
</script>

<section class="hud-panel now-playing" data-testid="playback-panel">
  <div class="panel-band">
    <span class="panel-label">Tocando agora</span>
    {#if !botOnline}
      <span class="stale" data-testid="playback-stale">bot fora do ar</span>
    {/if}
    <span class="stamp" data-testid="playback-state">{playbackState}</span>
  </div>
  {#if playback === null}
    <p class="data-value is-empty" data-testid="playback-empty">
      {connected ? "Voz conectada, sem sessão" : "Nenhuma sessão ativa"}
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
      {connected ? "Reconectar a saída" : "Conecte uma saída para começar"}
    </button>
  {:else}
    <div class="now-playing__body">
      <Thumbnail
        src={track?.thumbnail ?? ""}
        alt={track?.title ?? "Tocando agora"}
        className="now-playing__art"
        size={96}
      />
      <div class="now-playing__meta">
        <p class="now-playing__title" data-testid="now-playing">
          {track?.title ?? "Nada tocando"}
        </p>
        <p class="now-playing__line">
          {sourceLine || "Origem desconhecida"}
        </p>
        <div class="rating">
          <Readout
            label="Tempo"
            value={`${formatDuration($positionSeconds)} / ${formatDuration(
              track?.duration,
            )}`}
            testid="playback-progress"
          />
          <Readout
            label="Repetição"
            value={loopModeLabel(playback.loop_mode)}
          />
          <Readout label="Volume" value={formatVolume(playback.volume)} />
          <Readout label="Camadas" value={layersCountLabel(layers.length)} />
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
    border: 1px solid var(--rule-strong);
    border-radius: var(--radius-key);
  }

  .now-playing__meta {
    display: flex;
    flex-direction: column;
    gap: 0.75rem;
    min-width: 0;
  }

  .now-playing__title {
    margin: 0;
    font-family: var(--font-display);
    font-weight: 700;
    font-size: 1.375rem;
    line-height: 1.15;
    letter-spacing: -0.01em;
    color: var(--sand);
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
  }

  .now-playing__line {
    margin: 0;
    font-size: 0.8125rem;
    color: var(--label);
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
  }

  .now-playing__connect {
    margin-block-start: 0.85rem;
  }

  .stale {
    flex: none;
    font-family: var(--font-display);
    font-weight: 600;
    font-size: 0.6875rem;
    line-height: 1;
    letter-spacing: 0.12em;
    text-transform: uppercase;
    color: var(--alert);
    border: 1px solid var(--alert);
    border-radius: 2px;
    padding: 0.2rem 0.35rem;
  }

  @media (max-width: 30rem) {
    :global(.now-playing__art) {
      width: 4rem;
      height: 4rem;
    }

    .now-playing__title {
      font-size: 1.125rem;
      white-space: normal;
    }
  }
</style>
