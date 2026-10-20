<script lang="ts">
  import { appStore } from "$lib/store";
  import { formatSeen } from "$lib/format";
  import type { ConnectionEvent } from "$lib/contract/panel.gen";

  const viewers = $derived($appStore.presence?.viewers ?? []);
  const last = $derived($appStore.presence?.last_connection ?? null);

  function actorLabel(event: ConnectionEvent): string {
    return event.actor_name ?? "The bot";
  }

  function actionLabel(event: ConnectionEvent): string {
    return event.action === "connect" ? "linked" : "released";
  }
</script>

<section
  class="hud-panel"
  data-testid="presence-panel"
  aria-labelledby="presence-title"
>
  <span class="panel-label" id="presence-title">Linked</span>
  {#if viewers.length === 0}
    <p class="data-value is-empty" data-testid="presence-empty">
      No one else is linked
    </p>
  {:else}
    <ul class="roster" data-testid="roster">
      {#each viewers as viewer (viewer.user_id)}
        <li class="roster__row" data-testid="viewer-row">
          <span class="roster__name">
            {viewer.display_name || viewer.username}
          </span>
          <span class="roster__channel">
            {viewer.channel_name ?? "No channel"}
          </span>
          <span class="roster__seen" data-testid="viewer-seen">
            {formatSeen(viewer.seen_at)}
          </span>
        </li>
      {/each}
    </ul>
  {/if}
  {#if last}
    <p class="system-note" data-testid="last-connection">
      {actorLabel(last)}
      {actionLabel(last)}
      {last.channel_name ?? ""}
    </p>
  {/if}
</section>

<style>
  .roster {
    margin: 0;
    padding: 0;
    list-style: none;
  }

  .roster__row {
    display: grid;
    grid-template-columns: minmax(0, 1fr) minmax(0, 1fr) auto;
    align-items: baseline;
    gap: 0.5rem;
    padding-block: 0.4rem;
    border-bottom: 1px solid var(--rule);
  }

  .roster__name {
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
    color: var(--sand);
  }

  .roster__channel,
  .roster__seen {
    font-size: 0.75rem;
    letter-spacing: 0.02em;
    color: var(--dim);
  }

  .roster__channel {
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
  }

  .roster__seen {
    font-variant-numeric: tabular-nums;
  }
</style>
