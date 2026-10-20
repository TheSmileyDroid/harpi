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
  import ConnectedPanel from "./ConnectedPanel.svelte";
  import Readout from "./Readout.svelte";
  import TransportBar from "./TransportBar.svelte";

  let {
    link,
    stale,
    onrefresh,
    onresync,
    onsignout,
    api,
  }: {
    link: string;
    stale: boolean;
    onrefresh: () => Promise<boolean>;
    onresync: () => Promise<void>;
    onsignout: () => Promise<void>;
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

  const kbdLabel = /Mac|iPhone|iPad/.test(navigator.userAgent)
    ? "⌘ K"
    : "Ctrl K";
</script>

<svelte:window onkeydown={onGlobalKeydown} />

<main class="app-container" id="shell" data-stale={stale}>
  <header class="placard-bar">
    <span class="placard brand">
      <img
        class="brand__mark"
        src="/brand/harpi-smiley-mark.svg"
        alt=""
        aria-hidden="true"
      />
      <h1 class="page-title brand__name">Harpi</h1>
    </span>
    <OutputPicker {api} {link} {onresync} />
    {#if stale}
      <span class="stale-tag" data-testid="stale-tag" role="status">
        Stale
      </span>
    {/if}
    <button
      type="button"
      class="hud-btn bar__key"
      onclick={() => appStore.openSearch()}
      data-testid="open-search"
    >
      Search <span class="bar__kbd">{kbdLabel}</span>
    </button>
    <button
      type="button"
      class="hud-btn"
      onclick={() => void onsignout()}
      data-testid="sign-out"
    >
      Sign out
    </button>
  </header>

  <span class="visually-hidden" role="status" aria-live="polite">
    Bot {botOnline ? "online" : "offline"}; panel link {link}{stale
      ? "; readings stale"
      : ""}
  </span>

  <div class="console">
    <section class="console__main" aria-label="Music">
      <NowPlaying />
      <QueuePanel {api} />
    </section>

    <aside class="console__rail" aria-label="Layers and session">
      {#if layersOpen}
        <LayersPanel {api} />
        <button
          type="button"
          class="hud-btn rail__key"
          onclick={() => (layersOpen = false)}
          data-testid="layers-toggle"
        >
          Hide layers
        </button>
      {:else}
        <button
          type="button"
          class="hud-btn rail__key"
          onclick={() => (layersOpen = true)}
          data-testid="layers-reopen"
        >
          Show layers
        </button>
      {/if}

      <section
        class="hud-panel"
        data-testid="connection-panel"
        aria-label="Session"
      >
        <span class="panel-label">Session</span>
        <div class="rating">
          <Readout
            label="Bot"
            value={$appStore.bot.online ? "Online" : "Offline"}
            testid="bot-online"
          />
          <Readout label="Voice" value={voiceLabel} testid="connection" />
        </div>
        {#if !botOnline}
          <p class="system-note" data-testid="bot-offline-note">
            Bot offline — playback and voice are unavailable until it
            reconnects.
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

      <ConnectedPanel />
    </aside>
  </div>

  <TransportBar {api} />
</main>

<SearchPanel {api} />

<style>
  .brand {
    gap: 0.55rem;
    padding-inline: 0.55rem;
  }

  .brand__mark {
    display: block;
    block-size: 1.6rem;
    inline-size: auto;
    image-rendering: pixelated;
  }

  .brand__name {
    font-size: 0.85rem;
    letter-spacing: 0.24em;
  }

  .bar__key {
    margin-inline-start: auto;
  }

  .bar__kbd {
    font-size: 0.6875rem;
    letter-spacing: 0.1em;
    color: var(--dim);
    transition: color var(--motion-quick) ease;
  }

  .hud-btn:hover .bar__kbd {
    color: var(--sand);
  }

  .console {
    display: grid;
    flex: 1 1 auto;
    grid-template-columns: minmax(0, 1fr);
    grid-template-rows: minmax(0, 1fr);
    gap: 1rem;
  }

  .console__main {
    display: flex;
    flex-direction: column;
    flex: 1 1 auto;
    gap: 1rem;
    min-width: 0;
    min-block-size: 0;
  }

  .console__rail {
    display: flex;
    flex-direction: column;
    gap: 1rem;
    min-width: 0;
  }

  .rail__key {
    align-self: stretch;
  }

  @media (prefers-reduced-motion: no-preference) {
    .console__rail {
      animation: plate-rise var(--motion-settle) var(--ease-arrive);
    }
  }

  @media (min-width: 56rem) {
    .console {
      grid-template-columns: minmax(0, 1fr) 15.5rem;
      align-items: start;
    }

    .console__main {
      align-self: stretch;
    }
  }

  @media (max-width: 30rem) {
    .placard-bar {
      gap: 0.35rem;
    }

    .bar__kbd {
      display: none;
    }
  }
</style>
