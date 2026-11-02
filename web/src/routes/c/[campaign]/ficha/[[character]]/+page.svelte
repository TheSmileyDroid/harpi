<script lang="ts">
  import { resolve } from "$app/paths";
  import { page } from "$app/state";
  import { createApiClient } from "$lib/api";
  import { castInitials, castStateNote, submitNote } from "$lib/cast";
  import ConflictQueue from "$lib/components/ConflictQueue.svelte";
  import SheetEditor from "$lib/components/SheetEditor.svelte";
  import {
    conflictNote,
    conflictsForSheet,
    type SheetDecision,
  } from "$lib/conflicts";
  import type {
    CampaignDetail,
    CharacterCard,
    CharacterDetail,
    SheetConflictField,
    SheetDetail,
  } from "$lib/contract/panel.gen";
  import { phaseForError } from "$lib/phase";
  import type { LoadPhase } from "$lib/phase";
  import { sheetStateNote, statusLabel } from "$lib/sheet";

  let phase = $state<LoadPhase>("loading");
  let role = $state<CampaignDetail["role"] | null>(null);
  let detail = $state<CharacterDetail | null>(null);
  let cards = $state<CharacterCard[]>([]);
  let resubmitting = $state(false);
  let resubmitFailure = $state("");
  let resubmitNotice = $state("");
  let conflicts = $state<SheetConflictField[]>([]);
  let deciding = $state<string | null>(null);
  let recoveryBusy = $state(false);
  let recoveryFailure = $state("");
  let recoveryNotice = $state("");

  const api = createApiClient();
  const slug = $derived(page.params.campaign ?? "");
  const selected = $derived(page.params.character ?? "");
  const sheetConflicts = $derived(
    conflictsForSheet(
      conflicts,
      detail?.kind === "sheet" ? detail.sheet?.id : undefined,
    ),
  );
  const sheetReadOnly = $derived(
    (detail?.kind === "sheet" ? detail.sheet?.read_only : false) === true ||
      sheetConflicts.length > 0,
  );

  async function load(campaign: string, character: string) {
    phase = "loading";
    detail = null;
    try {
      role = (await api.campaign(campaign)).role;
      if (character) {
        detail = await api.campaignCharacter(campaign, character);
      } else {
        cards = (await api.campaignCharacters(campaign)).characters;
      }
      await refreshConflicts(campaign);
      phase = "ready";
    } catch (error) {
      role = null;
      cards = [];
      phase = phaseForError(error);
    }
  }

  $effect(() => {
    void load(slug, selected);
  });

  async function refreshConflicts(campaign: string) {
    try {
      conflicts = (await api.conflicts(campaign)).conflicts;
    } catch {
      conflicts = [];
    }
  }

  async function decide(conflict: SheetConflictField, decision: SheetDecision) {
    if (deciding !== null) return;
    deciding = conflict.id;
    recoveryFailure = "";
    recoveryNotice = "";
    try {
      await api.resolveConflict(slug, conflict.id, { decision });
      await load(slug, selected);
      recoveryNotice = "Conflito resolvido.";
    } catch (error) {
      recoveryFailure = conflictNote(error);
    } finally {
      deciding = null;
    }
  }

  async function restore() {
    if (detail?.kind !== "sheet" || !detail.sheet || recoveryBusy) return;
    recoveryBusy = true;
    recoveryFailure = "";
    recoveryNotice = "";
    try {
      await api.restoreSheet(slug, detail.sheet.id);
      await load(slug, selected);
      recoveryNotice = "Ficha restaurada no vault.";
    } catch (error) {
      recoveryFailure = conflictNote(error);
    } finally {
      recoveryBusy = false;
    }
  }

  async function forget() {
    if (detail?.kind !== "sheet" || !detail.sheet || recoveryBusy) return;
    recoveryBusy = true;
    recoveryFailure = "";
    recoveryNotice = "";
    try {
      await api.forgetSheet(slug, detail.sheet.id);
      await load(slug, selected);
      recoveryNotice = "Ficha esquecida.";
    } catch (error) {
      recoveryFailure = conflictNote(error);
    } finally {
      recoveryBusy = false;
    }
  }

  function updateSheet(fresh: SheetDetail) {
    if (detail?.kind === "sheet") {
      detail = { ...detail, sheet: fresh };
    }
  }

  function reloadSheet() {
    void load(slug, selected);
  }

  async function resubmit() {
    if (detail?.kind !== "sheet" || !detail.sheet || resubmitting) return;
    resubmitting = true;
    resubmitFailure = "";
    resubmitNotice = "";
    try {
      updateSheet(await api.submitSheet(slug, detail.sheet.id));
      resubmitNotice = "Ficha reenviada para aprovação.";
    } catch (error) {
      resubmitFailure = submitNote(error);
    } finally {
      resubmitting = false;
    }
  }
</script>

<svelte:head>
  <title>Ficha — Harpi</title>
</svelte:head>

<section class="hud-panel sheet" data-testid="sheet" aria-label="Ficha">
  <div class="panel-band">
    <h1 class="panel-label">Ficha</h1>
    {#if detail?.kind === "sheet" && detail.sheet}
      <span class="panel-band__meta" data-testid="sheet-status">
        {statusLabel(detail.sheet.status)}
      </span>
    {/if}
  </div>

  {#if phase !== "ready"}
    <p class="system-note" data-testid="sheet-state">
      {selected ? sheetStateNote(phase) : castStateNote(phase)}
    </p>
    {#if phase === "unavailable" || phase === "failed"}
      <button
        class="hud-btn sheet__retry"
        type="button"
        data-testid="sheet-retry"
        onclick={() => load(slug, selected)}
      >
        Tentar de novo
      </button>
    {/if}
  {:else if !selected}
    {#if cards.length === 0}
      <p class="system-note" data-testid="sheet-state">
        Nenhum personagem revelado ainda.
      </p>
    {:else}
      <ul class="sheet__picker">
        {#each cards as card (card.id)}
          <li>
            <a
              class="sheet__pick"
              href={resolve("/c/[campaign]/ficha/[[character]]", {
                campaign: slug,
                character: card.id,
              })}
              data-testid="sheet-pick"
            >
              <span class="sheet__pick-name">{card.name}</span>
              {#if card.concept}
                <span class="sheet__pick-concept">{card.concept}</span>
              {/if}
            </a>
          </li>
        {/each}
      </ul>
    {/if}
  {:else if detail?.kind === "card"}
    {@render identity(detail.card)}
    <p class="system-note" data-testid="sheet-card-note">
      A ficha mecânica fica visível só para o dono e o narrador.
    </p>
  {:else if detail?.kind === "sheet" && detail.sheet}
    {@const sheet = detail.sheet}
    {@render identity(detail.card)}

    {#if sheet.status === "pending"}
      <p class="placard sheet__banner" data-testid="sheet-pending">
        Ficha pendente de aprovação.
      </p>
    {/if}
    {#if sheet.review_note}
      <p class="placard sheet__banner" data-testid="sheet-review">
        Devolvida: {sheet.review_note}
      </p>
      {#if role !== "narrator"}
        <div class="sheet__resubmit">
          <button
            class="hud-btn"
            type="button"
            data-testid="sheet-resubmit"
            disabled={resubmitting}
            onclick={resubmit}
          >
            Reenviar para aprovação
          </button>
          {#if resubmitting}
            <span class="system-note">Enviando…</span>
          {/if}
        </div>
      {/if}
    {/if}
    {#if resubmitFailure}
      <p class="panel-error" role="alert" data-testid="sheet-resubmit-error">
        <span class="stamp is-hazard">Perigo</span>
        <span>{resubmitFailure}</span>
      </p>
    {/if}
    {#if resubmitNotice}
      <p class="placard sheet__banner" data-testid="sheet-resubmit-notice">
        {resubmitNotice}
      </p>
    {/if}
    {#if sheetReadOnly}
      <p class="placard sheet__banner" data-testid="sheet-readonly">
        {sheet.state === "missing"
          ? "Somente leitura: o arquivo sumiu do vault."
          : sheetConflicts.length || sheet.state === "conflict"
            ? "Somente leitura até a decisão dos conflitos."
            : "Somente leitura."}
      </p>
    {/if}
    {#if sheet.state === "missing"}
      <p class="system-note" data-testid="sheet-missing">
        O arquivo não está no vault. Restaurar regrava a última versão aceita
        com revisão nova; esquecer para de acompanhar esta ficha.
      </p>
      <div class="sheet__recovery">
        <button
          class="hud-btn hud-btn--primary"
          type="button"
          data-testid="sheet-restore"
          disabled={recoveryBusy}
          onclick={restore}
        >
          Restaurar
        </button>
        <button
          class="hud-btn hud-btn-danger"
          type="button"
          data-testid="sheet-forget"
          disabled={recoveryBusy}
          onclick={forget}
        >
          Esquecer
        </button>
        {#if recoveryBusy}
          <span class="system-note">Gravando…</span>
        {/if}
      </div>
    {/if}
    {#if recoveryFailure}
      <p class="panel-error" role="alert" data-testid="sheet-recovery-error">
        <span class="stamp is-hazard">Perigo</span>
        <span>{recoveryFailure}</span>
      </p>
    {/if}
    {#if recoveryNotice}
      <p class="placard sheet__banner" data-testid="sheet-recovery-notice">
        {recoveryNotice}
      </p>
    {/if}
    {#if sheetConflicts.length}
      <ConflictQueue
        conflicts={sheetConflicts}
        busy={deciding}
        onresolve={decide}
      />
    {/if}
    {#if sheet.error}
      <p class="panel-error" role="alert" data-testid="sheet-error">
        <span class="stamp is-hazard">Perigo</span>
        <span>{sheet.error}</span>
      </p>
    {/if}

    <SheetEditor
      {slug}
      {sheet}
      onupdate={updateSheet}
      onreload={reloadSheet}
      onconflict={() => void refreshConflicts(slug)}
    />
  {/if}
</section>

{#snippet identity(card: CharacterCard)}
  <div class="sheet__header">
    <div class="sheet__portrait" aria-hidden="true">
      {#if card.portrait}
        <img src={card.portrait} alt="" width="96" height="96" />
      {:else}
        <span class="sheet__initials">{castInitials(card.name)}</span>
      {/if}
    </div>
    <div class="sheet__identity">
      <h2 class="sheet__name">{card.name}</h2>
      {#if card.concept}
        <p class="sheet__concept">{card.concept}</p>
      {/if}
      {#if card.summary}
        <p class="sheet__summary">{card.summary}</p>
      {/if}
    </div>
  </div>
{/snippet}

<style>
  .sheet__header {
    display: flex;
    align-items: flex-start;
    gap: 0.85rem;
    margin-block-start: 0.85rem;
  }

  .sheet__portrait {
    display: grid;
    place-items: center;
    flex: none;
    inline-size: 6rem;
    block-size: 6rem;
    overflow: hidden;
    border: 1px solid var(--rule-strong);
    border-radius: var(--radius-key);
    background: var(--plate-2);
  }

  .sheet__portrait img {
    display: block;
    inline-size: 100%;
    block-size: 100%;
    object-fit: cover;
  }

  .sheet__initials {
    font-family: var(--font-label);
    font-weight: 700;
    font-size: 1.5rem;
    letter-spacing: 0.08em;
    color: var(--dim);
  }

  .sheet__identity {
    min-inline-size: 0;
  }

  .sheet__name {
    margin: 0;
    font-family: var(--font-display);
    font-weight: 700;
    font-size: 1.375rem;
    line-height: 1.15;
    color: var(--sand);
  }

  .sheet__concept {
    margin: 0.3rem 0 0;
    font-family: var(--font-value);
    font-size: 0.8125rem;
    line-height: 1.3;
    color: var(--sand);
  }

  .sheet__summary {
    margin: 0.35rem 0 0;
    font-family: var(--font-label);
    font-size: 0.8125rem;
    line-height: 1.4;
    color: var(--label);
  }

  .sheet__banner {
    margin-block-start: 0.85rem;
    font-family: var(--font-label);
    font-size: 0.6875rem;
    letter-spacing: 0.12em;
    text-transform: uppercase;
    color: var(--amber);
  }

  .sheet__recovery {
    display: flex;
    flex-wrap: wrap;
    align-items: center;
    gap: 0.5rem;
    margin-block-start: 0.5rem;
  }

  .sheet__recovery .system-note {
    margin: 0;
  }

  .sheet__resubmit {
    display: flex;
    flex-wrap: wrap;
    align-items: center;
    gap: 0.5rem;
    margin-block-start: 0.5rem;
  }

  .sheet__resubmit .system-note {
    margin: 0;
  }

  .sheet__picker {
    margin: 0.85rem 0 0;
    padding: 0;
    list-style: none;
  }

  .sheet__pick {
    display: flex;
    align-items: baseline;
    gap: 0.6rem;
    min-block-size: 2.5rem;
    padding: 0.55rem 0.6rem;
    border-block-start: 1px solid var(--rule);
    color: var(--sand);
    text-decoration: none;
  }

  .sheet__pick:hover {
    background: var(--plate-2);
  }

  .sheet__pick:focus-visible {
    outline: 2px solid var(--amber);
    outline-offset: 2px;
  }

  .sheet__pick-name {
    font-family: var(--font-display);
    font-weight: 700;
    font-size: 0.95rem;
  }

  .sheet__pick-concept {
    font-family: var(--font-label);
    font-size: 0.75rem;
    color: var(--dim);
  }

  .sheet__retry {
    margin-block-start: 0.75rem;
  }
</style>
