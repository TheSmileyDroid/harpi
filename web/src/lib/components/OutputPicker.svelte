<script lang="ts">
  import { get } from "svelte/store";
  import { onMount, tick } from "svelte";
  import { appStore } from "$lib/store";
  import { toasts } from "$lib/toasts";
  import StatusChip from "./StatusChip.svelte";
  import type { ApiClient } from "$lib/api";
  import type { StatusSnapshot } from "$lib/contract/panel.gen";

  let {
    api,
    link,
    onresync,
  }: { api: ApiClient; link: string; onresync: () => Promise<void> } = $props();

  let open = $state(false);
  let busy = $state(false);
  let root = $state<HTMLElement | null>(null);
  let firstSelect = $state<HTMLSelectElement | null>(null);
  let lastGuildId: string | null = null;

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
  const summary = $derived(
    activeGuild
      ? `${activeGuild.name}${activeChannel ? ` · ${activeChannel.name}` : ""}`
      : "Select output",
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

  function onGuildChange(event: Event) {
    const value = (event.currentTarget as HTMLSelectElement).value;
    appStore.selectChannel(null);
    appStore.selectGuild(value === "" ? null : value);
  }

  function onChannelChange(event: Event) {
    const value = (event.currentTarget as HTMLSelectElement).value;
    appStore.selectChannel(value === "" ? null : value);
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
      () => api.connect(effectiveGuildId, get(appStore).selectedChannelId),
      "Connected",
    );
  }

  function disconnect() {
    return mutate(() => api.disconnect(), "Disconnected");
  }

  function onWindowClick(event: MouseEvent) {
    if (open && root && !root.contains(event.target as Node)) open = false;
  }

  function onWindowKeydown(event: KeyboardEvent) {
    if (event.key === "Escape") open = false;
  }

  onMount(loadGuilds);

  $effect(() => {
    if (open) tick().then(() => firstSelect?.focus());
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
    onclick={() => (open = !open)}
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
        <label class="data-label" for="guild-select">Guild</label>
        <select
          id="guild-select"
          class="hud-input"
          bind:this={firstSelect}
          data-testid="guild-select"
          value={effectiveGuildId ?? ""}
          onchange={onGuildChange}
        >
          <option value="" disabled>Select a guild</option>
          {#each $appStore.guilds as guild (guild.id)}
            <option value={guild.id}>{guild.name}</option>
          {/each}
        </select>
      </div>
      {#if effectiveGuildId !== null}
        <div class="data-row">
          <label class="data-label" for="channel-select">Channel</label>
          <select
            id="channel-select"
            class="hud-input"
            data-testid="channel-select"
            value={$appStore.selectedChannelId ?? ""}
            onchange={onChannelChange}
          >
            <option value="" disabled>Select a channel</option>
            {#each $appStore.channels as channel (channel.id)}
              <option value={channel.id}>{channel.name}</option>
            {/each}
          </select>
        </div>
      {/if}
      <div class="action-strip">
        <button
          type="button"
          class="hud-btn"
          onclick={connect}
          disabled={busy ||
            !$appStore.bot.online ||
            $appStore.selectedChannelId === null}
          data-testid="connect"
        >
          Connect
        </button>
        {#if $appStore.connection.connected}
          <button
            type="button"
            class="hud-btn"
            onclick={disconnect}
            disabled={busy}
            data-testid="disconnect"
          >
            Disconnect
          </button>
        {/if}
      </div>
    </div>
  {/if}
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

  .output-picker__popover .hud-input {
    flex: 1;
    min-width: 0;
  }

  .output-picker__popover .action-strip {
    margin: 0.75rem -0.75rem -0.75rem;
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
