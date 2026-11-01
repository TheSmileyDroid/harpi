<script lang="ts">
  import {
    conflictLabel,
    conflictValue,
    type SheetDecision,
  } from "$lib/conflicts";
  import type { SheetConflictField } from "$lib/contract/panel.gen";

  let {
    conflicts,
    busy,
    onresolve,
  }: {
    conflicts: SheetConflictField[];
    busy: string | null;
    onresolve: (conflict: SheetConflictField, decision: SheetDecision) => void;
  } = $props();

  const OPTIONS: { decision: SheetDecision; label: string }[] = [
    { decision: "theirs", label: "Usar do vault" },
    { decision: "ours", label: "Usar do painel" },
  ];
</script>

<section
  class="conflicts"
  aria-labelledby="conflicts-label"
  data-testid="conflict-queue"
>
  <h2 class="panel-label" id="conflicts-label">Conflitos</h2>
  <p class="conflicts__note">
    O mesmo campo mudou no painel e no vault. A ficha fica somente leitura até a
    decisão de cada campo.
  </p>
  <ul class="conflicts__list">
    {#each conflicts as conflict (conflict.id)}
      <li class="conflict" data-testid="conflict-item">
        <h3 class="conflict__field" data-testid="conflict-field">
          {conflictLabel(conflict.field_path)}
        </h3>
        <div class="conflict__values">
          <div class="conflict__value">
            <span class="data-label">Base</span>
            <pre class="conflict__text">{conflictValue(conflict.base)}</pre>
          </div>
          <div class="conflict__value">
            <span class="data-label">Vault</span>
            <pre
              class="conflict__text"
              data-testid="conflict-theirs-value">{conflictValue(
                conflict.theirs,
              )}</pre>
          </div>
          <div class="conflict__value">
            <span class="data-label">Painel</span>
            <pre
              class="conflict__text"
              data-testid="conflict-ours-value">{conflictValue(
                conflict.ours,
              )}</pre>
          </div>
        </div>
        <div class="conflict__actions">
          {#each OPTIONS as option (option.decision)}
            <button
              class="hud-btn"
              type="button"
              data-testid={`conflict-${option.decision}`}
              disabled={busy !== null}
              onclick={() => onresolve(conflict, option.decision)}
            >
              {option.label}
            </button>
          {/each}
          {#if conflict.allow_both}
            <button
              class="hud-btn"
              type="button"
              data-testid="conflict-both"
              disabled={busy !== null}
              onclick={() => onresolve(conflict, "both")}
            >
              Manter os dois
            </button>
          {/if}
          {#if busy === conflict.id}
            <span class="system-note">Gravando…</span>
          {/if}
        </div>
      </li>
    {/each}
  </ul>
</section>

<style>
  .conflicts {
    margin-block-start: 0.85rem;
  }

  .conflicts__note {
    margin: 0.35rem 0 0;
    font-family: var(--font-label);
    font-size: 0.8125rem;
    line-height: 1.4;
    color: var(--label);
  }

  .conflicts__list {
    margin: 0.5rem 0 0;
    padding: 0;
    list-style: none;
  }

  .conflict {
    padding-block: 0.75rem;
    border-block-start: 1px solid var(--rule);
  }

  .conflict__field {
    margin: 0;
    font-family: var(--font-display);
    font-weight: 700;
    font-size: 0.95rem;
    color: var(--amber);
  }

  .conflict__values {
    display: grid;
    gap: 0.5rem;
    margin-block-start: 0.5rem;
  }

  .conflict__value {
    display: grid;
    gap: 0.2rem;
  }

  .conflict__text {
    margin: 0;
    padding: 0.4rem 0.6rem;
    overflow-x: auto;
    border: 1px solid var(--rule-strong);
    border-radius: var(--radius-key);
    background: var(--sunken);
    font-family: var(--font-value);
    font-size: 0.75rem;
    line-height: 1.4;
    color: var(--sand);
    white-space: pre-wrap;
    overflow-wrap: anywhere;
  }

  .conflict__actions {
    display: flex;
    flex-wrap: wrap;
    align-items: center;
    gap: 0.5rem;
    margin-block-start: 0.5rem;
  }

  .conflict .system-note {
    margin: 0;
  }

  @media (min-width: 48rem) {
    .conflict__values {
      grid-template-columns: repeat(3, minmax(0, 1fr));
    }
  }
</style>
