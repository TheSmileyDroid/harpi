<script lang="ts">
  import { appStore } from "$lib/store";
  import { toasts } from "$lib/toasts";
  import ConfirmDialog from "./ConfirmDialog.svelte";
  import { formatDuration } from "$lib/format";
  import type { ApiClient } from "$lib/api";
  import Thumbnail from "./Thumbnail.svelte";

  type Pending = { kind: "remove"; url: string } | { kind: "clear"; url: null };

  let { api }: { api: ApiClient } = $props();

  let busy = $state(false);
  let pending = $state<Pending | null>(null);

  const queue = $derived($appStore.playback?.queue ?? []);
  const hasSession = $derived($appStore.playback !== null);
  const confirmMessage = $derived(
    pending?.kind === "clear" ? "Clear the whole queue?" : "Remove this track?",
  );

  function askRemove(url: string) {
    pending = { kind: "remove", url };
  }

  function askClear() {
    pending = { kind: "clear", url: null };
  }

  function cancel() {
    pending = null;
  }

  async function confirm() {
    const action = pending;
    pending = null;
    if (!action || busy) return;
    busy = true;
    try {
      const snapshot =
        action.kind === "clear"
          ? await api.clearQueue()
          : await api.removeFromQueue(action.url);
      appStore.applyStatus(snapshot);
      toasts.push(
        action.kind === "clear" ? "Queue cleared" : "Removed from queue",
      );
    } catch {
      return;
    } finally {
      busy = false;
    }
  }
</script>

<section class="hud-panel" data-testid="queue-panel">
  <span class="panel-label">05 // Queue</span>
  {#if !hasSession}
    <p class="data-value is-empty" data-testid="queue-empty">No session</p>
  {:else if queue.length === 0}
    <p class="data-value is-empty" data-testid="queue-empty">Queue empty</p>
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
            onclick={() => askRemove(track.url)}
            disabled={busy}
            data-testid="queue-remove"
          >
            Del
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
  open={pending !== null}
  message={confirmMessage}
  onconfirm={confirm}
  oncancel={cancel}
/>
