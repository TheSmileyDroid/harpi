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
  }

  function onChannelChange(id: string | null) {
    appStore.selectChannel(id);
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
    <span class="data-label">Output</span>
    <span class="data-value" data-testid="guild-id">{summary}</span>
    <StatusChip online={$appStore.bot.online} />
    <span class="link-state" data-testid="link-state" data-link={link}>
      {linkLabels[link] ?? "LINKING"}
    </span>
  </button>

  {#if open}
    <div
      class="output-picker__popover"
      id="output-picker-popover"
      role="dialog"
      aria-label="Output"
    >
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
    gap: 0.6rem;
    max-width: 28rem;
    padding: 0.3rem 0.6rem;
    background: transparent;
    border: 1px solid var(--color-line);
    color: var(--color-primary);
    cursor: pointer;
  }

  .output-picker__trigger:hover {
    border-color: var(--color-amber-dim);
  }

  .output-picker__trigger:focus-visible {
    outline: 1px solid var(--color-amber-bright);
    outline-offset: 2px;
  }

  .output-picker__trigger .data-label {
    inline-size: auto;
  }

  .output-picker__trigger .data-value {
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
  }

  .output-picker__popover {
    position: absolute;
    inset-block-start: calc(100% + 0.35rem);
    inset-inline-start: 0;
    z-index: 40;
    min-width: min(22rem, 90vw);
    padding: 0.75rem;
    background: var(--color-surface-2);
    border: 1px solid var(--color-line);
    outline: 1px solid var(--color-line-strong);
    outline-offset: 2px;
  }

  .output-picker__popover .data-row {
    padding-block: 0.35rem;
  }

  .output-picker__popover :global(.hud-select) {
    flex: 1;
    min-width: 0;
  }

  .output-picker__popover .action-strip {
    margin: 0.75rem -0.75rem -0.75rem;
  }

  .output-picker__popover .system-note {
    margin: 0.35rem 0 0;
    font-size: 0.7rem;
    letter-spacing: 0.05em;
    color: var(--color-amber-dim);
  }

  @media (max-width: 30rem) {
    .output-picker {
      order: 3;
      flex: 1 1 100%;
    }

    .output-picker__trigger {
      width: 100%;
      max-width: none;
    }
  }
</style>
