<script lang="ts">
  import { resolve } from "$app/paths";
  import { page } from "$app/state";
  import { createApiClient } from "$lib/api";
  import { castInitials, castStateNote } from "$lib/cast";
  import type { CharacterCard, CharacterDetail } from "$lib/contract/panel.gen";
  import { phaseForError } from "$lib/phase";
  import type { LoadPhase } from "$lib/phase";
  import {
    itemLabel,
    sheetStateNote,
    skillsByRank,
    statusLabel,
  } from "$lib/sheet";

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

    <div class="rating sheet__readouts">
      <div class="rating__cell">
        <span class="data-label">Recarga</span>
        <span class="data-value">{sheet.refresh ?? "—"}</span>
      </div>
      <div class="rating__cell">
        <span class="data-label">Pontos de destino</span>
        <span class="data-value">{sheet.fate_points ?? "—"}</span>
      </div>
    </div>

    <section
      class="sheet__section"
      aria-labelledby="sheet-aspects"
      data-testid="sheet-aspects"
    >
      <h2 class="panel-label" id="sheet-aspects">Aspectos</h2>
      <dl class="sheet__aspects">
        {#each sheet.aspects as aspect, index (index)}
          <div class="sheet__aspect">
            <dt class="data-label">{aspect.label}</dt>
            <dd class="data-value">{aspect.text || "—"}</dd>
          </div>
        {/each}
      </dl>
    </section>

    <section
      class="sheet__section"
      aria-labelledby="sheet-skills"
      data-testid="sheet-skills"
    >
      <h2 class="panel-label" id="sheet-skills">Perícias</h2>
      {#each skillsByRank(sheet.skills, sheet.ladder) as group (group.rank)}
        <div class="sheet__rank">
          <span class="sheet__rank-step">
            {group.label}
            {group.rank >= 0 ? `+${group.rank}` : group.rank}
          </span>
          <span class="sheet__rank-skills">
            {group.skills.map((skill) => skill.name).join(" · ")}
          </span>
        </div>
      {:else}
        <p class="system-note">Nenhuma perícia acima de 0.</p>
      {/each}
    </section>

    <section
      class="sheet__section"
      aria-labelledby="sheet-stunts"
      data-testid="sheet-stunts"
    >
      <h2 class="panel-label" id="sheet-stunts">Façanhas</h2>
      {#each sheet.stunts as stunt, index (index)}
        <div class="sheet__stunt">
          <span class="sheet__stunt-name">{stunt.name}</span>
          <span class="sheet__stunt-cost">
            {stunt.refresh_cost === 0
              ? "sem custo"
              : `${stunt.refresh_cost} de recarga`}
          </span>
          {#if stunt.text}
            <p class="sheet__stunt-text">{stunt.text}</p>
          {/if}
        </div>
      {:else}
        <p class="system-note">Nenhuma façanha.</p>
      {/each}
    </section>

    <section
      class="sheet__section"
      aria-labelledby="sheet-stress"
      data-testid="sheet-stress"
    >
      <h2 class="panel-label" id="sheet-stress">Estresse</h2>
      {#each sheet.stress as track (track.track)}
        <div class="sheet__track">
          <span class="data-label">{track.track}</span>
          <ol class="sheet__boxes">
            {#each track.boxes as box, index (index)}
              <li
                class="sheet__box"
                data-checked={box.checked}
                aria-label={`${track.track} ${box.value}${
                  box.checked ? " marcada" : " livre"
                }`}
              >
                {box.value}
              </li>
            {/each}
          </ol>
        </div>
      {/each}
    </section>

    <section
      class="sheet__section"
      aria-labelledby="sheet-consequences"
      data-testid="sheet-consequences"
    >
      <h2 class="panel-label" id="sheet-consequences">Consequências</h2>
      {#each sheet.consequences as slot (slot.severity)}
        <div class="sheet__consequence" data-filled={slot.text !== ""}>
          <span class="data-label">{slot.severity} (+{slot.value})</span>
          <span class="data-value">{slot.text || "Livre"}</span>
        </div>
      {/each}
    </section>

    <section
      class="sheet__section"
      aria-labelledby="sheet-extras"
      data-testid="sheet-extras"
    >
      <h2 class="panel-label" id="sheet-extras">Extras</h2>
      {#each sheet.extras as extra, index (index)}
        <div class="sheet__extra">
          <span class="data-label">{extra.kind}</span>
          <span class="sheet__extra-name">{extra.name}</span>
          {#if extra.cost !== null}
            <span class="sheet__extra-cost">custo {extra.cost}</span>
          {/if}
          {#if extra.text}
            <p class="sheet__extra-text">{extra.text}</p>
          {/if}
        </div>
      {:else}
        <p class="system-note">Nenhum extra.</p>
      {/each}
    </section>

    <section
      class="sheet__section"
      aria-labelledby="sheet-inventory"
      data-testid="sheet-inventory"
    >
      <h2 class="panel-label" id="sheet-inventory">Inventário</h2>
      <ul class="sheet__inventory">
        {#each sheet.inventory as entry, index (index)}
          <li class="sheet__item">
            <span class="sheet__item-name">{itemLabel(entry.item)}</span>
            <span class="sheet__item-qty">×{entry.qty}</span>
            {#if entry.note}
              <span class="sheet__item-note">{entry.note}</span>
            {/if}
          </li>
        {:else}
          <li class="system-note">Nenhum item.</li>
        {/each}
      </ul>
    </section>
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

  .sheet__readouts {
    margin-block-start: 0.85rem;
  }

  .sheet__readouts .data-label,
  .sheet__readouts .data-value {
    display: block;
  }

  .sheet__readouts .data-value {
    font-size: 0.9375rem;
    line-height: 1.2;
  }

  .sheet__section {
    margin-block-start: 1rem;
  }

  .sheet__aspects {
    display: grid;
    gap: 0.5rem;
    margin: 0;
  }

  .sheet__aspect {
    display: grid;
    gap: 0.15rem;
    padding-block: 0.4rem;
    border-block-start: 1px solid var(--rule);
  }

  .sheet__aspect:first-child {
    border-block-start: none;
    padding-block-start: 0;
  }

  .sheet__aspect .data-value {
    margin: 0;
  }

  .sheet__rank {
    display: flex;
    align-items: baseline;
    gap: 0.75rem;
    padding-block: 0.4rem;
    border-block-start: 1px solid var(--rule);
  }

  .sheet__rank:first-of-type {
    border-block-start: none;
  }

  .sheet__rank-step {
    flex: none;
    min-inline-size: 7rem;
    font-family: var(--font-label);
    font-weight: 600;
    font-size: 0.6875rem;
    letter-spacing: 0.12em;
    text-transform: uppercase;
    color: var(--amber);
  }

  .sheet__rank-skills {
    font-family: var(--font-value);
    font-size: 0.8125rem;
    line-height: 1.5;
    color: var(--sand);
  }

  .sheet__stunt,
  .sheet__extra {
    padding-block: 0.5rem;
    border-block-start: 1px solid var(--rule);
  }

  .sheet__stunt:first-of-type,
  .sheet__extra:first-of-type {
    border-block-start: none;
  }

  .sheet__stunt-name,
  .sheet__extra-name {
    font-family: var(--font-value);
    font-size: 0.8125rem;
    color: var(--sand);
  }

  .sheet__stunt-cost,
  .sheet__extra-cost {
    margin-inline-start: 0.5rem;
    font-family: var(--font-label);
    font-size: 0.6875rem;
    letter-spacing: 0.12em;
    text-transform: uppercase;
    color: var(--dim);
  }

  .sheet__stunt-text,
  .sheet__extra-text {
    margin: 0.3rem 0 0;
    font-family: var(--font-label);
    font-size: 0.8125rem;
    line-height: 1.4;
    color: var(--label);
  }

  .sheet__track {
    display: flex;
    align-items: center;
    gap: 0.75rem;
    padding-block: 0.4rem;
    border-block-start: 1px solid var(--rule);
  }

  .sheet__track:first-of-type {
    border-block-start: none;
  }

  .sheet__boxes {
    display: flex;
    gap: 0.35rem;
    margin: 0;
    padding: 0;
    list-style: none;
  }

  .sheet__box {
    display: grid;
    place-items: center;
    inline-size: 2rem;
    block-size: 2rem;
    border: 1px solid var(--rule-strong);
    border-radius: var(--radius-key);
    font-family: var(--font-value);
    font-size: 0.8125rem;
    color: var(--dim);
    background: var(--sunken);
  }

  .sheet__box[data-checked="true"] {
    border-color: var(--amber);
    color: var(--amber);
    background: var(--plate-2);
  }

  .sheet__consequence {
    display: grid;
    grid-template-columns: 9rem minmax(0, 1fr);
    gap: 0.75rem;
    align-items: baseline;
    padding-block: 0.4rem;
    border-block-start: 1px solid var(--rule);
  }

  .sheet__consequence:first-of-type {
    border-block-start: none;
  }

  .sheet__consequence[data-filled="true"] .data-value {
    color: var(--sand);
  }

  .sheet__consequence[data-filled="false"] .data-value {
    color: var(--faint);
  }

  .sheet__inventory {
    margin: 0;
    padding: 0;
    list-style: none;
  }

  .sheet__item {
    display: flex;
    align-items: baseline;
    gap: 0.5rem;
    padding-block: 0.4rem;
    border-block-start: 1px solid var(--rule);
  }

  .sheet__item:first-child {
    border-block-start: none;
  }

  .sheet__item-name {
    font-family: var(--font-value);
    font-size: 0.8125rem;
    color: var(--sand);
  }

  .sheet__item-qty {
    font-family: var(--font-value);
    font-size: 0.75rem;
    color: var(--sand);
  }

  .sheet__item-note {
    font-family: var(--font-label);
    font-size: 0.75rem;
    color: var(--dim);
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

  @media (max-width: 48rem) {
    .sheet__consequence {
      grid-template-columns: minmax(0, 1fr);
      gap: 0.15rem;
    }

    .sheet__rank {
      flex-direction: column;
      gap: 0.2rem;
    }
  }
</style>
