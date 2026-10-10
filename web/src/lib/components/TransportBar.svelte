<script lang="ts">
  import { appStore } from "$lib/store";
  import { formatDuration } from "$lib/format";
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
  const duration = $derived(playback?.current_music?.duration ?? 0);
  const title = $derived(playback?.current_music?.title ?? "Nothing playing");
  const isPaused = $derived(playback?.is_paused === true);
  const serverRatio = $derived(
    duration > 0 ? (playback?.progress ?? 0) / duration : 0,
  );
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
    if (!duration || busy || seeking) return;
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
    if (!duration || busy || seeking) return;
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
    <span class="progress-readout" data-testid="progress-readout">
      {formatDuration(displayRatio * duration)} / {formatDuration(duration)} //
      {title}
    </span>
  {/if}
</div>
