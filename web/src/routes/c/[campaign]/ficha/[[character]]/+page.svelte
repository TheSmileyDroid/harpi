<script lang="ts">
  import { resolve } from "$app/paths";
  import { page } from "$app/state";
  import { createApiClient } from "$lib/api";
  import { castInitials, castStateNote } from "$lib/cast";
  import SheetEditor from "$lib/components/SheetEditor.svelte";
  import type {
    CharacterCard,
    CharacterDetail,
    SheetDetail,
  } from "$lib/contract/panel.gen";
  import { phaseForError } from "$lib/phase";
  import type { LoadPhase } from "$lib/phase";
  import { sheetStateNote, statusLabel } from "$lib/sheet";

  let phase = $state<LoadPhase>("loading");
  let detail = $state<CharacterDetail | null>(null);
  let cards = $state<CharacterCard[]>([]);

  const api = createApiClient();
  const slug = $derived(page.params.campaign ?? "");
  const selected = $derived(page.params.character ?? "");

  async function load(campaign: string, character: string) {
    phase = "loading";
    detail = null;
    try {
      if (character) {
        detail = await api.campaignCharacter(campaign, character);
      } else {
        cards = (await api.campaignCharacters(campaign)).characters;
      }
      phase = "ready";
    } catch (error) {
      cards = [];
      phase = phaseForError(error);
    }
  }

  $effect(() => {
    void load(slug, selected);
  });

  function updateSheet(fresh: SheetDetail) {
    if (detail?.kind === "sheet") {
      detail = { ...detail, sheet: fresh };
    }
  }

  function reloadSheet() {
    void load(slug, selected);
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
    {#if sheet.read_only}
      <p class="placard sheet__banner" data-testid="sheet-readonly">
        Somente leitura.
      </p>
    {/if}
    {#if sheet.error}
      <p class="panel-error" role="alert" data-testid="sheet-error">
        <span class="stamp is-hazard">Hazard</span>
        <span>{sheet.error}</span>
      </p>
    {/if}

    <SheetEditor {slug} {sheet} onupdate={updateSheet} onreload={reloadSheet} />
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
