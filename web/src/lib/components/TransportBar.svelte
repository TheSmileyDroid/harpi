<script lang="ts">
  import { appStore } from "$lib/store";
  import { formatDuration } from "$lib/format";
  import { positionSeconds } from "$lib/playback-clock";
  import {
    nextLoopMode,
    pointerRatio,
    seekDisplayRatio,
    seekTarget,
  } from "$lib/transport";
  import type { ApiClient } from "$lib/api";
  import type { StatusSnapshot } from "$lib/contract/panel.gen";
  import VolumeSlider from "./VolumeSlider.svelte";

  let { api }: { api: ApiClient } = $props();

  let busy = $state(false);
  let seeking = $state(false);
  let seekRatio = $state(0);
  let activePointer = $state<number | null>(null);
  let track = $state<HTMLElement | null>(null);
  let bar = $state<HTMLElement | null>(null);

  $effect(() => {
    const element = bar;
    if (!element) return;
    const apply = () =>
      document.documentElement.style.setProperty(
        "--transport-height",
        `${element.offsetHeight}px`,
      );
    apply();
    const observer = new ResizeObserver(apply);
    observer.observe(element);
    return () => {
      observer.disconnect();
      document.documentElement.style.removeProperty("--transport-height");
    };
  });

  const playback = $derived($appStore.playback);
  const ready = $derived(playback !== null);
  const botOnline = $derived($appStore.bot.online);
  const keysDisabled = $derived(busy || !botOnline);
  const duration = $derived(playback?.current_music?.duration ?? 0);
  const title = $derived(playback?.current_music?.title ?? "Nothing playing");
  const isPaused = $derived(playback?.is_paused === true);
  const serverRatio = $derived(duration > 0 ? $positionSeconds / duration : 0);
  const displayRatio = $derived(
    seekDisplayRatio(seeking, seekRatio, serverRatio),
  );

  async function act(fn: () => Promise<StatusSnapshot>) {
    if (busy) return;
    busy = true;
    try {
      const snapshot = await fn();
      appStore.applyStatus(snapshot);
    } catch {
      return;
    } finally {
      busy = false;
    }
  }

  function togglePlay() {
    return isPaused ? act(() => api.resume()) : act(() => api.pause());
  }

  function skip() {
    return act(() => api.skip());
  }

  function previous() {
    return act(() => api.previous());
  }

  function cycleLoop() {
    return act(() => api.loop(nextLoopMode(playback?.loop_mode)));
  }

  function ratioAt(clientX: number): number {
    if (!track) return 0;
    const rect = track.getBoundingClientRect();
    return pointerRatio(clientX - rect.left, rect.width);
  }

  function onSeekDown(event: PointerEvent) {
    if (!duration || busy || seeking || !botOnline) return;
    seeking = true;
    activePointer = event.pointerId;
    seekRatio = ratioAt(event.clientX);
    track?.setPointerCapture?.(event.pointerId);
  }

  function onSeekMove(event: PointerEvent) {
    if (!seeking || event.pointerId !== activePointer) return;
    seekRatio = ratioAt(event.clientX);
  }

  function cancelSeek() {
    seeking = false;
    activePointer = null;
  }

  async function onSeekUp(event: PointerEvent) {
    if (!seeking || event.pointerId !== activePointer) return;
    seekRatio = ratioAt(event.clientX);
    const target = seekTarget(seekRatio, duration);
    seeking = false;
    activePointer = null;
    await act(() => api.seek(target));
  }

  function seekTo(position: number) {
    return act(() => api.seek(position));
  }

  function onSeekKeydown(event: KeyboardEvent) {
    if (!duration || busy || seeking || !botOnline) return;
    const current = displayRatio * duration;
    let target: number | null = null;
    if (event.key === "ArrowRight") target = current + 5;
    else if (event.key === "ArrowLeft") target = current - 5;
    else if (event.key === "PageUp") target = current + 15;
    else if (event.key === "PageDown") target = current - 15;
    else if (event.key === "Home") target = 0;
    else if (event.key === "End") target = duration;
    if (target === null) return;
    event.preventDefault();
    seekTo(Math.max(0, Math.min(duration, target)));
  }

  async function sendVolume(value: number) {
    const snapshot = await api.volume(value);
    appStore.applyStatus(snapshot);
  }
</script>

<div
  class="transport-bar"
  class:is-paused={isPaused}
  class:is-seeking={seeking}
  class:is-offline={!botOnline}
  bind:this={bar}
  data-testid="transport"
>
  {#if !ready}
    <span class="progress-readout is-empty" data-testid="transport-empty">
      No session — connect an output to begin.
    </span>
  {:else}
    <button
      type="button"
      class="hud-btn"
      onclick={previous}
      disabled={keysDisabled}
      title={botOnline ? undefined : "Bot offline"}
      data-testid="previous"
    >
      Prev
    </button>
    <button
      type="button"
      class="hud-btn hud-btn--primary"
      onclick={togglePlay}
      disabled={keysDisabled}
      title={botOnline ? undefined : "Bot offline"}
      data-testid="play-pause"
    >
      {isPaused ? "Play" : "Pause"}
    </button>
    <button
      type="button"
      class="hud-btn"
      onclick={skip}
      disabled={keysDisabled}
      title={botOnline ? undefined : "Bot offline"}
      data-testid="skip"
    >
      Skip
    </button>
    <button
      type="button"
      class="hud-btn"
      onclick={cycleLoop}
      disabled={keysDisabled}
      title={`Loop ${playback?.loop_mode} — next ${nextLoopMode(playback?.loop_mode)}`}
      data-testid="loop"
    >
      Loop {playback?.loop_mode}
    </button>
    <div
      class="progress-track"
      bind:this={track}
      data-duration={duration}
      title="Click or drag to seek"
      role="slider"
      tabindex="0"
      aria-label="Seek"
      aria-disabled={!botOnline}
      aria-valuemin="0"
      aria-valuemax={duration}
      aria-valuenow={Math.round(displayRatio * duration)}
      onpointerdown={onSeekDown}
      onpointermove={onSeekMove}
      onpointerup={onSeekUp}
      onpointercancel={cancelSeek}
      onlostpointercapture={cancelSeek}
      onkeydown={onSeekKeydown}
      data-testid="seek-track"
    >
      <div
        class="progress-fill"
        style="width: {(displayRatio * 100).toFixed(1)}%"
      ></div>
    </div>
    <VolumeSlider
      gain={playback?.volume ?? 0}
      send={sendVolume}
      label="Volume"
      disabled={!botOnline}
      controlTestid="volume-control"
      sliderTestid="volume-slider"
      valueTestid="volume-value"
    />
    <span class="progress-readout" data-testid="progress-readout">
      {#if !botOnline}<span class="transport-warn">Bot offline</span>
      {/if}<span class="readout-time"
        >{formatDuration(displayRatio * duration)} / {formatDuration(
          duration,
        )}</span
      ><span class="readout-title">{title}</span>
    </span>
  {/if}
  <footer class="status-strip" data-testid="status-strip">Harpi panel</footer>
</div>
