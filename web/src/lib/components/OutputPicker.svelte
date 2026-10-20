<script lang="ts">
  import { onMount, tick } from "svelte";
  import { appStore } from "$lib/store";
  import { toasts } from "$lib/toasts";
  import StatusChip from "./StatusChip.svelte";
  import ConfirmDialog from "./ConfirmDialog.svelte";
  import Select from "./Select.svelte";
  import type { ApiClient } from "$lib/api";
  import type { StatusSnapshot } from "$lib/contract/panel.gen";

  let {
    api,
    link,
    onresync,
  }: { api: ApiClient; link: string; onresync: () => Promise<void> } = $props();

  let busy = $state(false);
  let confirmingDisconnect = $state(false);
  let root = $state<HTMLElement | null>(null);
  let lastGuildId: string | null = null;
  let followedChannelId: string | null = null;

  const open = $derived($appStore.outputOpen);
  const effectiveGuildId = $derived(
    $appStore.pendingGuildId ?? $appStore.guildId,
  );
  const activeGuild = $derived(
    $appStore.guilds.find((guild) => guild.id === effectiveGuildId) ?? null,
  );
  const activeChannel = $derived(
    $appStore.channels.find(
      (channel) => channel.id === $appStore.selectedChannelId,
    ) ?? null,
  );
  const connected = $derived($appStore.connection.connected);
  const hasSession = $derived($appStore.playback !== null);
  const targetChannelId = $derived(
    $appStore.selectedChannelId ?? $appStore.connection.channel_id,
  );
  const summary = $derived(
    activeGuild
      ? `${activeGuild.name}${activeChannel ? ` · ${activeChannel.name}` : ""}`
      : "Select output",
  );
  const connectHint = $derived(
    !$appStore.bot.online
      ? "Bot offline"
      : effectiveGuildId === null
        ? "Select a guild"
        : targetChannelId === null
          ? "Select a channel"
          : null,
  );

  const linkLabels: Record<string, string> = {
    connected: "LINK LIVE",
    reconnecting: "LINK LOST",
    connecting: "LINKING",
  };

  async function loadGuilds() {
    const payload = await api.guilds().catch(() => null);
    if (!payload) return;
    appStore.setGuilds(payload.guilds);
  }

  async function loadChannels(guildId: string | null) {
    if (guildId === null) {
      appStore.setChannels([]);
      return;
    }
    const payload = await api.channels(guildId).catch(() => null);
    if (payload) appStore.setChannels(payload.channels);
  }

  function onGuildChange(id: string | null) {
    appStore.selectChannel(null);
    appStore.selectGuild(id);
    if (id === null) {
      void persistSelection(null, null);
      return;
    }
    return persistGuild(id);
  }

  async function persistGuild(id: string) {
    busy = true;
    try {
      const snapshot = await api.select(id, null);
      appStore.applyStatus(snapshot);
      appStore.selectGuild(null);
      await onresync();
    } catch {
      return;
    } finally {
      busy = false;
    }
  }

  function onChannelChange(id: string | null) {
    appStore.selectChannel(id);
    if (id !== null && effectiveGuildId !== null) {
      void persistSelection(effectiveGuildId, id);
    }
  }

  async function persistSelection(
    guildId: string | null,
    channelId: string | null,
    silent = false,
  ) {
    const snapshot = await api
      .select(guildId, channelId, silent)
      .catch(() => null);
    if (snapshot) appStore.applyStatus(snapshot);
  }

  async function mutate(
    action: () => Promise<StatusSnapshot>,
    message: string,
  ) {
    busy = true;
    try {
      const snapshot = await action();
      appStore.applyStatus(snapshot);
      toasts.push(message);
      await loadChannels(effectiveGuildId);
      await onresync();
    } catch {
      return;
    } finally {
      busy = false;
    }
  }

  function connect() {
    return mutate(
      () => api.connect(effectiveGuildId, targetChannelId),
      "Connected",
    );
  }

  function askDisconnect() {
    confirmingDisconnect = true;
  }

  function cancelDisconnect() {
    confirmingDisconnect = false;
  }

  function confirmDisconnect() {
    confirmingDisconnect = false;
    return mutate(() => api.disconnect(), "Disconnected");
  }

  function onWindowClick(event: MouseEvent) {
    if (open && root && !root.contains(event.target as Node)) {
      appStore.closeOutput();
    }
  }

  function onWindowKeydown(event: KeyboardEvent) {
    if (event.key === "Escape") appStore.closeOutput();
  }

  onMount(loadGuilds);

  $effect(() => {
    if (open) {
      tick().then(() =>
        root
          ?.querySelector<HTMLButtonElement>('[data-testid="guild-select"]')
          ?.focus(),
      );
    }
  });

  $effect(() => {
    const guildId = effectiveGuildId;
    if (guildId === lastGuildId) return;
    lastGuildId = guildId;
    loadChannels(guildId);
  });

  $effect(() => {
    const live = $appStore.connection;
    const liveChannelId = live.connected ? live.channel_id : null;
    if (liveChannelId === followedChannelId) return;
    followedChannelId = liveChannelId;
    if (liveChannelId === null) return;
    appStore.selectChannel(liveChannelId);
    if ($appStore.guildId !== null) {
      void persistSelection($appStore.guildId, liveChannelId, true);
    }
    if (!$appStore.channels.some((channel) => channel.id === liveChannelId)) {
      void loadChannels($appStore.guildId);
    }
  });
</script>

<svelte:window onclick={onWindowClick} onkeydown={onWindowKeydown} />

<div class="output-picker" bind:this={root}>
  <button
    type="button"
    class="output-picker__trigger"
    aria-expanded={open}
    aria-haspopup="dialog"
    aria-controls="output-picker-popover"
    onclick={() => appStore.toggleOutput()}
    data-testid="output-picker"
  >
    <span class="placard">
      <span class="placard__label">Output</span>
      <span class="placard__value" data-testid="guild-id">{summary}</span>
    </span>
    <span class="placard" data-flipped={!$appStore.bot.online}>
      <span class="placard__label">Carrier</span>
      <StatusChip online={$appStore.bot.online} />
    </span>
    <span class="placard">
      <span class="placard__label">Voice</span>
      <span class="link-state" data-testid="link-state" data-link={link}>
        {linkLabels[link] ?? "LINKING"}
      </span>
    </span>
  </button>

  {#if open}
    <div
      class="output-picker__popover"
      id="output-picker-popover"
      role="dialog"
      aria-label="Output"
    >
      <span class="panel-label">Output</span>
      <div class="data-row">
        <span class="data-label">Guild</span>
        <Select
          label="Guild"
          placeholder="Select a guild"
          testid="guild-select"
          optionTestid="guild-option"
          disabled={busy}
          value={effectiveGuildId}
          options={$appStore.guilds.map((guild) => ({
            id: guild.id,
            label: guild.name,
          }))}
          onchange={onGuildChange}
        />
      </div>
      {#if effectiveGuildId !== null}
        <div class="data-row">
          <span class="data-label">Channel</span>
          <Select
            label="Channel"
            placeholder="Select a channel"
            testid="channel-select"
            optionTestid="channel-option"
            disabled={busy}
            value={$appStore.selectedChannelId}
            options={$appStore.channels.map((channel) => ({
              id: channel.id,
              label: channel.name,
            }))}
            onchange={onChannelChange}
          />
        </div>
      {/if}
      {#if connectHint}
        <p class="system-note" data-testid="connect-hint">{connectHint}</p>
      {/if}
      {#if connected && !hasSession}
        <p class="system-note" data-testid="session-idle-note">
          Voice link up, session idle — reconnect to take control.
        </p>
      {/if}
      <div class="action-strip">
        <button
          type="button"
          class="hud-btn"
          onclick={connect}
          disabled={busy || !$appStore.bot.online || targetChannelId === null}
          data-testid="connect"
        >
          {connected ? "Reconnect" : "Connect"}
        </button>
        {#if connected}
          <button
            type="button"
            class="hud-btn"
            onclick={askDisconnect}
            disabled={busy}
            data-testid="disconnect"
          >
            Disconnect
          </button>
        {/if}
      </div>
    </div>
  {/if}

  <ConfirmDialog
    open={confirmingDisconnect}
    message="Disconnect the bot from voice?"
    testid="disconnect-confirm"
    cancelTestid="disconnect-confirm-cancel"
    executeTestid="disconnect-confirm-execute"
    onconfirm={confirmDisconnect}
    oncancel={cancelDisconnect}
  />
</div>

<style>
  .output-picker {
    position: relative;
    min-width: 0;
  }

  .output-picker__trigger {
    display: flex;
    align-items: center;
    gap: 0.5rem;
    max-width: 100%;
    padding: 0;
    background: none;
    border: 0;
    cursor: pointer;
  }

  .output-picker__trigger .placard {
    transition:
      background-color var(--motion-quick) ease,
      box-shadow var(--motion-quick) ease;
  }

  .output-picker__trigger:hover .placard {
    background: color-mix(in srgb, var(--sand) 8%, var(--plate-2));
  }

  .output-picker__trigger:focus-visible {
    outline: 2px solid var(--amber);
    outline-offset: 2px;
    border-radius: var(--radius-key);
  }

  .output-picker__popover {
    position: absolute;
    inset-block-start: calc(100% + 0.5rem);
    inset-inline-start: 0;
    z-index: 40;
    min-width: min(24rem, 90vw);
    padding: 0.85rem;
    background: var(--plate-2);
    border: 1px solid var(--rule-strong);
    border-radius: var(--radius-plate);
    box-shadow: 0 0.75rem 1.6rem rgb(0 0 0 / 0.55);
  }

  @media (prefers-reduced-motion: no-preference) {
    .output-picker__popover {
      animation: overlay-wipe 200ms var(--ease-arrive);
    }
  }

  .output-picker__popover :global(.hud-select) {
    flex: 1;
    min-width: 0;
  }

  .output-picker__popover .action-strip {
    margin: 0.85rem -0.85rem -0.85rem;
  }

  @media (max-width: 30rem) {
    .output-picker {
      flex: 1 1 100%;
    }

    .output-picker__trigger {
      flex-wrap: wrap;
      width: 100%;
    }

    .output-picker__trigger .placard {
      flex: 1 1 8rem;
    }

    .output-picker__trigger .placard:first-child {
      flex: 1 1 100%;
    }
  }
</style>
