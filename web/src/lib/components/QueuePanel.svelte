<script lang="ts">
  import { flip } from "svelte/animate";
  import { appStore } from "$lib/store";
  import { toasts } from "$lib/toasts";
  import { flipParams } from "$lib/motion";
  import ConfirmDialog from "./ConfirmDialog.svelte";
  import EmptyState from "./EmptyState.svelte";
  import { formatCount, formatDuration } from "$lib/format";
  import type { ApiClient } from "$lib/api";
  import Thumbnail from "./Thumbnail.svelte";

  let { api }: { api: ApiClient } = $props();

  let busy = $state(false);
  let confirmingClear = $state(false);

  const queue = $derived($appStore.playback?.queue ?? []);
  const hasSession = $derived($appStore.playback !== null);
  const maxDuration = $derived(
    queue.reduce((max, track) => Math.max(max, track.duration), 0),
  );
  const totalDuration = $derived(
    queue.reduce((sum, track) => sum + track.duration, 0),
  );

  function gaugePercent(duration: number): string {
    if (maxDuration <= 0) return "0";
    return ((duration / maxDuration) * 100).toFixed(1);
  }

  async function removeTrack(url: string) {
    if (busy) return;
    busy = true;
    try {
      const snapshot = await api.removeFromQueue(url);
      appStore.applyStatus(snapshot);
      toasts.push("Removed from queue", {
        label: "Re-add",
        run: () => undoRemove(url),
      });
    } catch {
      return;
    } finally {
      busy = false;
    }
  }

  async function undoRemove(url: string) {
    try {
      const snapshot = await api.queue(url);
      appStore.applyStatus(snapshot);
    } catch {
      return;
    }
  }

  function askClear() {
    confirmingClear = true;
  }

  function cancelClear() {
    confirmingClear = false;
  }

  async function confirmClear() {
    confirmingClear = false;
    if (busy) return;
    busy = true;
    try {
      const snapshot = await api.clearQueue();
      appStore.applyStatus(snapshot);
      toasts.push("Queue cleared");
    } catch {
      return;
    } finally {
      busy = false;
    }
  }
</script>

<section class="hud-panel queue-panel" data-testid="queue-panel">
  <div class="panel-band">
    <span class="panel-label">Queue</span>
    {#if queue.length > 0}
      <span class="panel-band__meta">
        {formatCount(queue.length, "track")} · {formatDuration(totalDuration)}
      </span>
    {/if}
  </div>
  {#if !hasSession}
    <p class="data-value is-empty" data-testid="queue-empty">
      No active session
    </p>
  {:else if queue.length === 0}
    <EmptyState
      message="Queue empty — search to add tracks."
      testid="queue-empty"
      buttonTestid="queue-search"
      onsearch={() => appStore.openSearch()}
    />
  {:else}
    <ul class="queue-list">
      {#each queue as track, index (track.url)}
        <li
          class="data-row queue-row"
          data-testid="queue-row"
          style="--row-delay: {Math.min(index, 6) * 30}ms"
          animate:flip={flipParams()}
        >
          <span class="queue-index row-meta">
            {String(index + 1).padStart(2, "0")}
          </span>
          <Thumbnail
            src={track.thumbnail}
            alt={track.title}
            className="row-thumb"
            size={32}
          />
          <span class="data-title">{track.title}</span>
          <span class="row-gauge" aria-hidden="true">
            <span
              class="row-gauge__fill"
              style="width: {gaugePercent(track.duration)}%"
            ></span>
          </span>
          <span class="row-meta">
            {track.uploader} · {formatDuration(track.duration)}
          </span>
          <button
            type="button"
            class="hud-btn hud-btn-danger"
            onclick={() => removeTrack(track.url)}
            disabled={busy}
            aria-label={`Remove ${track.title} from queue`}
            data-testid="queue-remove"
          >
            Remove
          </button>
        </li>
      {/each}
    </ul>
    <div class="action-strip">
      <button
        type="button"
        class="hud-btn hud-btn-danger"
        onclick={askClear}
        disabled={busy}
        data-testid="queue-clear"
      >
        Clear queue
      </button>
    </div>
  {/if}
</section>

<ConfirmDialog
  open={confirmingClear}
  message="Clear the whole queue?"
  onconfirm={confirmClear}
  oncancel={cancelClear}
/>

<style>
  .queue-panel {
    display: flex;
    flex-direction: column;
    flex: 1 1 auto;
    min-block-size: 0;
  }

  .queue-list {
    flex: 1 1 auto;
    min-block-size: 0;
    max-block-size: 60vh;
    overflow-y: auto;
  }

  @media (min-width: 56rem) {
    .queue-list {
      max-block-size: none;
    }
  }
</style>
