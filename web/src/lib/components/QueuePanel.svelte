<script lang="ts">
  import { appStore } from "$lib/store";
  import { toasts } from "$lib/toasts";
  import ConfirmDialog from "./ConfirmDialog.svelte";
  import { formatDuration } from "$lib/format";
  import type { ApiClient } from "$lib/api";
  import Thumbnail from "./Thumbnail.svelte";

  let { api }: { api: ApiClient } = $props();

  let busy = $state(false);
  let confirmingClear = $state(false);

  const queue = $derived($appStore.playback?.queue ?? []);
  const hasSession = $derived($appStore.playback !== null);

  async function removeTrack(url: string) {
    if (busy) return;
    busy = true;
    try {
      const snapshot = await api.removeFromQueue(url);
      appStore.applyStatus(snapshot);
      toasts.push("Removed from queue", {
        label: "Undo",
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

<section class="hud-panel" data-testid="queue-panel">
  <span class="panel-label">02 // Queue</span>
  {#if !hasSession}
    <p class="data-value is-empty" data-testid="queue-empty">
      No active session
    </p>
  {:else if queue.length === 0}
    <p class="data-value is-empty" data-testid="queue-empty">
      Queue empty — search to add tracks.
    </p>
  {:else}
    <ul class="queue-list">
      {#each queue as track, index (track.url)}
        <li class="data-row queue-row" data-testid="queue-row">
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
  .queue-list {
    max-height: 40vh;
    overflow-y: auto;
  }
</style>
