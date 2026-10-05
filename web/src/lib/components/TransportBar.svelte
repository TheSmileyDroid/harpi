<script lang="ts">
  import { appStore } from "$lib/store";
  import { toasts } from "$lib/toasts";
  import { formatDuration } from "$lib/format";
  import {
    nextLoopMode,
    pointerRatio,
    seekDisplayRatio,
    seekTarget,
  } from "$lib/transport";
  import type { ApiClient } from "$lib/api";
  import type { StatusSnapshot } from "$lib/types";
  import VolumeSlider from "./VolumeSlider.svelte";

  let { api }: { api: ApiClient } = $props();

  let busy = $state(false);
  let seeking = $state(false);
  let seekRatio = $state(0);
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
  const duration = $derived(playback?.current_music?.duration ?? 0);
  const title = $derived(playback?.current_music?.title ?? "Nothing playing");
  const isPaused = $derived(playback?.is_paused === true);
  const serverRatio = $derived(
    duration > 0 ? (playback?.progress ?? 0) / duration : 0,
  );
  const displayRatio = $derived(
    seekDisplayRatio(seeking, seekRatio, serverRatio),
  );

  async function act(fn: () => Promise<StatusSnapshot>, message: string) {
    if (busy) return;
    busy = true;
    try {
      const snapshot = await fn();
      appStore.applyStatus(snapshot);
      toasts.push(message);
    } catch {
      return;
    } finally {
      busy = false;
    }
  }

  function togglePlay() {
    return isPaused
      ? act(() => api.resume(), "Resumed")
      : act(() => api.pause(), "Paused");
  }

  function skip() {
    return act(() => api.skip(), "Skipped");
  }

  function previous() {
    return act(() => api.previous(), "Previous track");
  }

  function cycleLoop() {
    return act(
      () => api.loop(nextLoopMode(playback?.loop_mode)),
      "Loop changed",
    );
  }

  function ratioAt(clientX: number): number {
    if (!track) return 0;
    const rect = track.getBoundingClientRect();
    return pointerRatio(clientX - rect.left, rect.width);
  }

  function onSeekDown(event: PointerEvent) {
    if (!duration || busy) return;
    seeking = true;
    seekRatio = ratioAt(event.clientX);
    track?.setPointerCapture?.(event.pointerId);
  }

  function onSeekMove(event: PointerEvent) {
    if (!seeking) return;
    seekRatio = ratioAt(event.clientX);
  }

  async function onSeekUp(event: PointerEvent) {
    if (!seeking) return;
    seekRatio = ratioAt(event.clientX);
    const target = seekTarget(seekRatio, duration);
    if (busy) {
      seeking = false;
      return;
    }
    busy = true;
    try {
      const snapshot = await api.seek(target);
      appStore.applyStatus(snapshot);
      toasts.push("Position set");
    } catch {
      return;
    } finally {
      busy = false;
      seeking = false;
    }
  }

  async function sendVolume(value: number) {
    const snapshot = await api.volume(value);
    appStore.applyStatus(snapshot);
    toasts.push("Volume changed");
  }
</script>

<div
  class="transport-bar"
  class:is-paused={isPaused}
  bind:this={bar}
  data-testid="transport"
>
  {#if !ready}
    <span class="progress-readout is-empty" data-testid="transport-empty">
      TRANSPORT // NO SESSION
    </span>
  {:else}
    <button
      type="button"
      class="hud-btn"
      onclick={previous}
      disabled={busy}
      data-testid="previous"
    >
      Prev
    </button>
    <button
      type="button"
      class="hud-btn"
      onclick={togglePlay}
      disabled={busy}
      data-testid="play-pause"
    >
      {isPaused ? "Play" : "Pause"}
    </button>
    <button
      type="button"
      class="hud-btn"
      onclick={skip}
      disabled={busy}
      data-testid="skip"
    >
      Skip
    </button>
    <button
      type="button"
      class="hud-btn"
      onclick={cycleLoop}
      disabled={busy}
      data-testid="loop"
    >
      Loop {playback?.loop_mode}
    </button>
    <VolumeSlider
      gain={playback?.volume ?? 0}
      send={sendVolume}
      label="Volume"
      controlTestid="volume-control"
      sliderTestid="volume-slider"
      valueTestid="volume-value"
    />
    <div
      class="progress-track"
      bind:this={track}
      data-duration={duration}
      title="Click or drag to seek"
      role="slider"
      tabindex="0"
      aria-label="Seek"
      aria-valuemin="0"
      aria-valuemax={duration}
      aria-valuenow={Math.round(displayRatio * duration)}
      onpointerdown={onSeekDown}
      onpointermove={onSeekMove}
      onpointerup={onSeekUp}
      onpointercancel={onSeekUp}
      data-testid="seek-track"
    >
      <div
        class="progress-fill"
        style="width: {(displayRatio * 100).toFixed(1)}%"
      ></div>
    </div>
    <span class="progress-readout" data-testid="progress-readout">
      {formatDuration(displayRatio * duration)} / {formatDuration(duration)} //
      {title}
    </span>
  {/if}
</div>
