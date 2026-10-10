<script lang="ts">
  import { get } from "svelte/store";
  import { appStore } from "$lib/store";
  import { toasts } from "$lib/toasts";
  import type { ApiClient } from "$lib/api";
  import OutputPicker from "./OutputPicker.svelte";
  import NowPlaying from "./NowPlaying.svelte";
  import SearchPanel from "./SearchPanel.svelte";
  import QueuePanel from "./QueuePanel.svelte";
  import LayersPanel from "./LayersPanel.svelte";
  import TransportBar from "./TransportBar.svelte";

  let {
    link,
    onrefresh,
    onresync,
    api,
  }: {
    link: string;
    onrefresh: () => Promise<boolean>;
    onresync: () => Promise<void>;
    api: ApiClient;
  } = $props();

  let refreshing = $state(false);
  let reconnecting = $state(false);
  let layersOpen = $state(true);

  const botOnline = $derived($appStore.bot.online);
  const connected = $derived($appStore.connection.connected);
  const hasSession = $derived($appStore.playback !== null);
  const voiceChannel = $derived(
    $appStore.channels.find(
      (channel) => channel.id === $appStore.connection.channel_id,
    ) ?? null,
  );
  const voiceLabel = $derived(
    !botOnline
      ? "Unavailable"
      : connected
        ? voiceChannel
          ? `Linked to ${voiceChannel.name}`
          : $appStore.connection.channel_id
            ? `Linked to ${$appStore.connection.channel_id}`
            : "Linked"
        : "Not connected",
  );

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

  async function reconnect() {
    const state = get(appStore);
    const guildId = state.guildId;
    const channelId = state.connection.channel_id;
    if (!guildId || !channelId) {
      appStore.openOutput();
      return;
    }
    reconnecting = true;
    try {
      const snapshot = await api.connect(guildId, channelId);
      appStore.applyStatus(snapshot);
      toasts.push("Reconnected");
      await onresync();
    } catch {
      return;
    } finally {
      reconnecting = false;
    }
  }

  function onGlobalKeydown(event: KeyboardEvent) {
    if ((event.metaKey || event.ctrlKey) && event.key.toLowerCase() === "k") {
      event.preventDefault();
      appStore.openSearch();
    }
  }
</script>

<svelte:window onkeydown={onGlobalKeydown} />

<main class="app-container" id="shell">
  <header class="topbar">
    <span class="logo">
      <img class="logo-mark" src="/harpi-logo.svg" alt="" aria-hidden="true" />
      <span class="logo-text">HARPI</span>
    </span>
    <OutputPicker {api} {link} {onresync} />
    <button
      type="button"
      class="hud-btn topbar__search"
      onclick={() => appStore.openSearch()}
      data-testid="open-search"
    >
      Search <span class="topbar__kbd">Ctrl K</span>
    </button>
  </header>

  <span class="visually-hidden" role="status" aria-live="polite">
    Bot {botOnline ? "online" : "offline"}; panel link {link}
  </span>

  <section class="region" aria-labelledby="region-music-title">
    <h1 class="page-title region-heading" id="region-music-title">Music</h1>
    <div class="music-layout">
      <div class="music-main">
        <NowPlaying />
        <QueuePanel {api} />
      </div>
      {#if layersOpen}
        <aside class="layers-rail" aria-labelledby="region-layers-title">
          <div class="layers-rail__head">
            <h2 class="region-title" id="region-layers-title">Layers</h2>
            <button
              type="button"
              class="hud-btn"
              onclick={() => (layersOpen = false)}
              data-testid="layers-toggle"
            >
              Hide
            </button>
          </div>
          <LayersPanel {api} />
        </aside>
      {/if}
    </div>
    {#if !layersOpen}
      <button
        type="button"
        class="hud-btn rail-reopen"
        onclick={() => (layersOpen = true)}
        data-testid="layers-reopen"
      >
        Show layers
      </button>
    {/if}
  </section>

  <section class="region" aria-labelledby="region-system-title">
    <h2 class="region-title" id="region-system-title">System</h2>
    <section class="hud-panel" data-testid="connection-panel">
      <span class="panel-label">04 // Session</span>
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
          {voiceLabel}
        </span>
      </div>
      {#if !botOnline}
        <p class="system-note" data-testid="bot-offline-note">
          Bot offline — playback and voice are unavailable until it reconnects.
        </p>
      {:else if connected && !hasSession}
        <p class="system-note" data-testid="session-idle-note">
          Voice link up, session idle — reconnect to take control.
        </p>
      {/if}
      <div class="action-strip">
        {#if connected}
          <button
            type="button"
            class="hud-btn"
            onclick={reconnect}
            disabled={reconnecting}
            data-testid="reconnect"
          >
            {reconnecting ? "Reconnecting…" : "Reconnect"}
          </button>
        {/if}
        <button
          type="button"
          class="hud-btn"
          onclick={refresh}
          disabled={refreshing}
          data-testid="refresh"
        >
          {refreshing ? "Checking…" : "Refresh"}
        </button>
      </div>
    </section>
  </section>

  <TransportBar {api} />

  <footer class="status-strip">
    <span>Harpi panel</span>
  </footer>
</main>

<SearchPanel {api} />

<style>
  .topbar {
    display: flex;
    align-items: center;
    gap: 0.75rem;
    padding: 0.5rem 1rem;
    border-bottom: 1px solid var(--color-line);
    margin-bottom: 1rem;
  }

  .logo {
    display: flex;
    align-items: center;
    gap: 0.5rem;
    margin-inline-end: auto;
  }

  .logo-text {
    font-family: var(--font-display);
    font-weight: 600;
    font-size: 1rem;
    letter-spacing: 0.3em;
    color: var(--color-primary);
  }

  .logo-mark {
    display: block;
    height: 1.5rem;
    width: auto;
    image-rendering: pixelated;
  }

  .topbar__search {
    display: flex;
    align-items: center;
    gap: 0.5rem;
    flex: none;
  }

  .topbar__kbd {
    font-size: 0.6rem;
    letter-spacing: 0.15em;
    color: var(--color-amber-dim);
  }

  .hud-btn:hover .topbar__kbd {
    color: var(--color-background);
  }

  .region {
    margin-block-start: 1.5rem;
  }

  .region-heading {
    margin: 0 0 0.5rem;
  }

  .region-title {
    margin: 0 0 0.5rem;
    font-family: var(--font-display);
    font-weight: 600;
    font-size: 1rem;
    letter-spacing: 0.2em;
    text-transform: uppercase;
    color: var(--color-primary);
  }

  .music-layout {
    display: grid;
    grid-template-columns: minmax(0, 1fr);
    gap: 1rem;
  }

  .music-main {
    display: flex;
    flex-direction: column;
    gap: 1rem;
    min-width: 0;
  }

  .layers-rail {
    min-width: 0;
  }

  .layers-rail__head {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 0.5rem;
    margin-bottom: 0.5rem;
  }

  .layers-rail__head .region-title {
    margin: 0;
  }

  .system-note {
    margin: 0.35rem 0 0;
    font-size: 0.7rem;
    letter-spacing: 0.05em;
    color: var(--color-amber-dim);
  }

  .rail-reopen {
    display: block;
    margin-inline-start: auto;
    margin-block-start: 0.75rem;
  }

  @media (min-width: 48rem) {
    .music-layout {
      grid-template-columns: minmax(0, 1fr) 20rem;
      align-items: start;
    }
  }

  @media (max-width: 30rem) {
    .topbar {
      flex-wrap: wrap;
    }

    .topbar__kbd {
      display: none;
    }

    .region {
      margin-block-start: 1rem;
    }
  }
</style>
