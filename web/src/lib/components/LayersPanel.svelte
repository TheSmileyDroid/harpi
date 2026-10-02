<script>
  import { appStore } from "$lib/store.js";
  import { toasts } from "$lib/toasts.js";
  import Thumbnail from "./Thumbnail.svelte";
  import ConfirmDialog from "./ConfirmDialog.svelte";
  import VolumeSlider from "./VolumeSlider.svelte";

  let { api } = $props();

  let busy = $state(false);
  let pending = $state(null);

  const layers = $derived($appStore.playback?.layers ?? []);
  const hasSession = $derived($appStore.playback !== null);
  const confirmMessage = $derived(
    pending ? `Remove layer "${pending.title}"?` : "Remove this layer?",
  );

  async function sendLayerVolume(id, value) {
    const snapshot = await api.setLayerVolume(id, value);
    appStore.applyStatus(snapshot);
    toasts.push("Layer volume changed");
  }

  function askRemove(layer) {
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
  <span class="panel-label">06 // Layers</span>
  {#if !hasSession}
    <p class="data-value is-empty" data-testid="layers-empty">No session</p>
  {:else if layers.length === 0}
    <p class="data-value is-empty" data-testid="layers-empty">No layers</p>
  {:else}
    <ul class="layer-list">
      {#each layers as layer, index (layer.id)}
        <li class="data-row layer-row" data-testid="layer-row">
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
            data-testid="layer-remove"
          >
            Del
          </button>
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
