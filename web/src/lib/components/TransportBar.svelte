<script>
  import { appStore } from "$lib/store.js";
  import { toasts } from "$lib/toasts.js";
  import { createDebouncer } from "$lib/debounce.js";
  import { formatDuration } from "$lib/format.js";
  import {
    nextLoopMode,
    pointerRatio,
    seekDisplayRatio,
    seekTarget,
    volumeGain,
    volumePosition,
  } from "$lib/transport.js";

  let { api } = $props();

  let busy = $state(false);
  let seeking = $state(false);
  let seekRatio = $state(0);
  let track = $state(null);
  let volumePos = $state(0);
  let adjustingVolume = $state(false);
  const volumeDebouncer = createDebouncer({ delay: 300 });

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
  const gain = $derived(volumeGain(volumePos));

  $effect(() => {
    if (adjustingVolume) return;
    volumePos = volumePosition(playback?.volume ?? 0);
  });

  async function act(fn, message) {
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

  function ratioAt(clientX) {
    if (!track) return 0;
    const rect = track.getBoundingClientRect();
    return pointerRatio(clientX - rect.left, rect.width);
  }

  function onSeekDown(event) {
    if (!duration || busy) return;
    seeking = true;
    seekRatio = ratioAt(event.clientX);
    track?.setPointerCapture?.(event.pointerId);
  }

  function onSeekMove(event) {
    if (!seeking) return;
    seekRatio = ratioAt(event.clientX);
  }

  async function onSeekUp(event) {
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

  function onVolumeInput() {
    adjustingVolume = true;
    volumeDebouncer.run(sendVolume);
  }

  async function sendVolume() {
    try {
      const snapshot = await api.volume(volumeGain(volumePos));
      appStore.applyStatus(snapshot);
      toasts.push("Volume changed");
    } catch {
      return;
    } finally {
      adjustingVolume = false;
    }
  }
</script>

<div class="transport-bar" class:is-paused={isPaused} data-testid="transport">
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
      Loop {playback.loop_mode}
    </button>
    <label class="volume-control" data-testid="volume-control">
      <input
        type="range"
        class="volume-slider"
        min="0"
        max="1"
        step="0.01"
        bind:value={volumePos}
        oninput={onVolumeInput}
        aria-label="Volume"
        data-testid="volume-slider"
      />
      <span class="volume-value" data-testid="volume-value">
        {gain.toFixed(2)}
      </span>
    </label>
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
