<script>
  import { appStore } from "$lib/store.js";
  import { toasts } from "$lib/toasts.js";
  import StatusChip from "./StatusChip.svelte";

  let { link, onrefresh } = $props();
  let refreshing = $state(false);

  const linkLabels = {
    connected: "LINK LIVE",
    reconnecting: "LINK LOST",
    connecting: "LINKING",
  };

  function percent(value) {
    if (typeof value !== "number" || Number.isNaN(value)) return "0%";
    return `${Math.round(value * 100)}%`;
  }

  async function refresh() {
    refreshing = true;
    try {
      if (await onrefresh()) {
        toasts.push("Status refreshed");
      }
    } finally {
      refreshing = false;
    }
  }
</script>

<main class="app-container" id="shell">
  <header role="banner">
    <span class="logo">
      <span class="logo-text">HARPI</span>
    </span>
    <span class="link-state" data-testid="link-state" data-link={link}>
      {linkLabels[link] ?? "LINKING"}
    </span>
    <StatusChip online={$appStore.bot.online} />
  </header>

  <div class="main-content">
    <div class="page-header">
      <h1 class="page-title">System status</h1>
    </div>

    <section class="hud-panel" data-testid="guild-panel">
      <span class="panel-label">01 // Guild</span>
      <div class="data-row">
        <span class="data-label">Selection</span>
        {#if $appStore.guildId === null}
          <span class="data-value is-empty" data-testid="guild-id">
            No guild selected
          </span>
        {:else}
          <span class="data-value" data-testid="guild-id">
            Guild {$appStore.guildId}
          </span>
        {/if}
      </div>
    </section>

    <section class="hud-panel" data-testid="connection-panel">
      <span class="panel-label">02 // Bot</span>
      <div class="data-row">
        <span class="data-label">Bot</span>
        <span class="data-value" data-testid="bot-online">
          {$appStore.bot.online ? "Online" : "Offline"}
        </span>
      </div>
      <div class="data-row">
        <span class="data-label">Voice</span>
        <span
          class="data-value"
          data-testid="connection"
          data-connected={$appStore.connection.connected}
        >
          {$appStore.connection.connected
            ? `Linked to ${$appStore.connection.channel_id}`
            : "Not connected"}
        </span>
      </div>
    </section>

    <section class="hud-panel" data-testid="playback-panel">
      <span class="panel-label">03 // Playback</span>
      {#if $appStore.playback === null}
        <p class="data-value is-empty" data-testid="playback-empty">
          No active session
        </p>
      {:else}
        <div class="data-row">
          <span class="data-label">Track</span>
          <span class="data-title" data-testid="now-playing">
            {$appStore.playback.current_music?.title ?? "Nothing playing"}
          </span>
        </div>
        <div class="data-row">
          <span class="data-label">State</span>
          <span class="data-value" data-testid="playback-state">
            {$appStore.playback.is_playing
              ? $appStore.playback.is_paused
                ? "Paused"
                : "Playing"
              : "Stopped"}
          </span>
        </div>
        <div class="data-row">
          <span class="data-label">Progress</span>
          <span class="data-value" data-testid="playback-progress">
            {percent($appStore.playback.progress)}
          </span>
        </div>
        <div class="data-row">
          <span class="data-label">Volume</span>
          <span class="data-value">{$appStore.playback.volume}</span>
        </div>
        <div class="data-row">
          <span class="data-label">Loop</span>
          <span class="data-value">{$appStore.playback.loop_mode}</span>
        </div>
        <div class="data-row">
          <span class="data-label">Queue</span>
          <span class="data-value">{$appStore.playback.queue.length}</span>
        </div>
        <div class="data-row">
          <span class="data-label">Layers</span>
          <span class="data-value">{$appStore.playback.layers.length}</span>
        </div>
        <div class="action-strip">
          <button
            class="hud-btn"
            type="button"
            onclick={refresh}
            disabled={refreshing}
            data-testid="refresh"
          >
            {refreshing ? "Checking…" : "Refresh"}
          </button>
        </div>
      {/if}
    </section>
  </div>

  <footer class="status-strip" role="contentinfo">
    <span>Harpi panel</span>
  </footer>
</main>

<style>
  .page-header {
    margin-block: 0.5rem 0.25rem;
  }

  header .logo-text {
    font-size: 1rem;
  }

  .link-state {
    font-family: var(--font-display);
    font-weight: 600;
    font-size: 0.7rem;
    letter-spacing: 0.15em;
    text-transform: uppercase;
    color: var(--color-amber-dim);
  }

  .link-state[data-link="reconnecting"] {
    color: var(--color-alert);
  }

  .action-strip {
    display: flex;
    justify-content: flex-end;
    margin: 0.75rem -1rem -1rem;
    padding: 0.35rem 0.5rem;
    border-top: 1px solid var(--color-line);
    background: var(--color-surface-2);
  }
</style>
