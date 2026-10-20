<script lang="ts">
  import { flip } from "svelte/animate";
  import { appStore } from "$lib/store";
  import { toasts } from "$lib/toasts";
  import { flipParams } from "$lib/motion";
  import Thumbnail from "./Thumbnail.svelte";
  import ConfirmDialog from "./ConfirmDialog.svelte";
  import EmptyState from "./EmptyState.svelte";
  import VolumeSlider from "./VolumeSlider.svelte";
  import { formatCount } from "$lib/format";
  import type { ApiClient } from "$lib/api";
  import type { Layer } from "$lib/contract/panel.gen";

  let { api }: { api: ApiClient } = $props();

  let busy = $state(false);
  let pending = $state<Layer | null>(null);

  const layers = $derived($appStore.playback?.layers ?? []);
  const hasSession = $derived($appStore.playback !== null);
  const confirmMessage = $derived(
    pending ? `Remove layer "${pending.title}"?` : "Remove this layer?",
  );

  async function sendLayerVolume(id: string, value: number) {
    const snapshot = await api.setLayerVolume(id, value);
    appStore.applyStatus(snapshot);
  }

  function askRemove(layer: Layer) {
    pending = layer;
  }

  function cancel() {
    pending = null;
  }

  async function confirm() {
    const layer = pending;
    pending = null;
    if (!layer || busy) return;
    busy = true;
    try {
      const snapshot = await api.removeLayer(layer.id);
      appStore.applyStatus(snapshot);
      toasts.push("Layer removed");
    } catch {
      return;
    } finally {
      busy = false;
    }
  }
</script>

<section class="hud-panel" data-testid="layers-panel">
  <div class="panel-band">
    <span class="panel-label">Layers</span>
    {#if layers.length > 0}
      <span class="panel-band__meta">{formatCount(layers.length, "layer")}</span
      >
    {/if}
  </div>
  {#if !hasSession}
    <p class="data-value is-empty" data-testid="layers-empty">
      No active session
    </p>
  {:else if layers.length === 0}
    <EmptyState
      message="No layers — add one from Search."
      testid="layers-empty"
      buttonTestid="layers-search"
      onsearch={() => appStore.openSearch()}
    />
  {:else}
    <ul class="layer-list">
      {#each layers as layer, index (layer.id)}
        <li
          class="layer-row"
          data-testid="layer-row"
          style="--row-delay: {Math.min(index, 6) * 25}ms"
          animate:flip={flipParams()}
        >
          <div class="layer-row__head">
            <span class="row-meta layer-index">
              {String(index + 1).padStart(2, "0")}
            </span>
            <Thumbnail
              src={layer.thumbnail}
              alt={layer.title}
              className="row-thumb"
              size={32}
            />
            <span class="data-title">{layer.title}</span>
          </div>
          <div class="layer-row__controls">
            <VolumeSlider
              gain={layer.volume}
              send={(value) => sendLayerVolume(layer.id, value)}
              label="Layer volume"
              className="layer-volume"
              controlTestid="layer-volume-control"
              sliderTestid="layer-volume"
              valueTestid="layer-volume-value"
            />
            <button
              type="button"
              class="hud-btn hud-btn-danger"
              onclick={() => askRemove(layer)}
              disabled={busy}
              aria-label={`Remove layer ${layer.title}`}
              data-testid="layer-remove"
            >
              Remove
            </button>
          </div>
        </li>
      {/each}
    </ul>
  {/if}
</section>

<ConfirmDialog
  open={pending !== null}
  message={confirmMessage}
  testid="layer-confirm-dialog"
  cancelTestid="layer-confirm-cancel"
  executeTestid="layer-confirm-execute"
  onconfirm={confirm}
  oncancel={cancel}
/>

<style>
  .layer-row {
    padding-block: 0.5rem;
    border-bottom: 1px solid var(--rule);
  }

  .layer-row__head {
    display: flex;
    align-items: center;
    gap: 0.5rem;
  }

  .layer-row__controls {
    display: flex;
    align-items: center;
    gap: 0.5rem;
    margin-block-start: 0.45rem;
  }

  .layer-row__controls :global(.layer-volume) {
    flex: 1;
  }
</style>
