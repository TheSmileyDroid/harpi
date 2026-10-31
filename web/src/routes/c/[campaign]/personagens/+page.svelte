<script lang="ts">
  import { onMount } from "svelte";
  import { resolve } from "$app/paths";
  import { page } from "$app/state";
  import { createApiClient } from "$lib/api";
  import { castInitials, castStateNote } from "$lib/cast";
  import { formatCount } from "$lib/format";
  import { phaseForError } from "$lib/phase";
  import type { LoadPhase } from "$lib/phase";
  import type { CharacterCard } from "$lib/contract/panel.gen";

  let phase = $state<LoadPhase>("loading");
  let cards = $state<CharacterCard[]>([]);

  const api = createApiClient();
  const slug = $derived(page.params.campaign ?? "");

  async function load(campaign: string) {
    phase = "loading";
    try {
      const payload = await api.campaignCharacters(campaign);
      cards = payload.characters;
      phase = "ready";
    } catch (error) {
      cards = [];
      phase = phaseForError(error);
    }
  }

  onMount(() => {
    void load(slug);
  });
</script>

<svelte:head>
  <title>Personagens — Harpi</title>
</svelte:head>

<section class="hud-panel cast" data-testid="cast" aria-label="Personagens">
  <div class="panel-band">
    <h1 class="panel-label">Personagens</h1>
    {#if phase === "ready"}
      <span class="panel-band__meta">
        {formatCount(cards.length, "personagem", "personagens")}
      </span>
    {/if}
  </div>

  {#if phase !== "ready"}
    <p class="system-note" data-testid="cast-state">{castStateNote(phase)}</p>
    {#if phase === "unavailable" || phase === "failed"}
      <button
        class="hud-btn cast__retry"
        type="button"
        data-testid="cast-retry"
        onclick={() => load(slug)}
      >
        Tentar de novo
      </button>
    {/if}
  {:else if cards.length === 0}
    <p class="system-note" data-testid="cast-state">
      Nenhum personagem revelado ainda.
    </p>
  {:else}
    <ul class="cast__list">
      {#each cards as card (card.id)}
        <li class="cast__card" data-testid="cast-card">
          <div class="cast__portrait" aria-hidden="true">
            {#if card.portrait}
              <img src={card.portrait} alt="" width="96" height="96" />
            {:else}
              <span class="cast__initials">{castInitials(card.name)}</span>
            {/if}
          </div>
          <div class="cast__body">
            <h2 class="cast__name">{card.name}</h2>
            {#if card.concept}
              <p class="cast__concept">{card.concept}</p>
            {/if}
            {#if card.summary}
              <p class="cast__summary">{card.summary}</p>
            {/if}
            <a
              class="cast__open"
              href={resolve("/c/[campaign]/ficha/[[character]]", {
                campaign: slug,
                character: card.id,
              })}
              data-testid="cast-open"
            >
              Abrir ficha
            </a>
          </div>
        </li>
      {/each}
    </ul>
  {/if}
</section>

<style>
  .cast__list {
    margin: 0;
    padding: 0;
    list-style: none;
  }

  .cast__card {
    display: flex;
    align-items: flex-start;
    gap: 0.85rem;
    padding-block: 0.75rem;
    border-block-start: 1px solid var(--rule);
  }

  .cast__card:first-child {
    border-block-start: none;
    padding-block-start: 0;
  }

  .cast__portrait {
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

  .cast__portrait img {
    display: block;
    inline-size: 100%;
    block-size: 100%;
    object-fit: cover;
  }

  .cast__initials {
    font-family: var(--font-label);
    font-weight: 700;
    font-size: 1.5rem;
    letter-spacing: 0.08em;
    color: var(--dim);
  }

  .cast__body {
    min-inline-size: 0;
  }

  .cast__name {
    margin: 0;
    font-family: var(--font-display);
    font-weight: 700;
    font-size: 1.125rem;
    line-height: 1.15;
    color: var(--sand);
  }

  .cast__concept {
    margin: 0.3rem 0 0;
    font-family: var(--font-value);
    font-size: 0.8125rem;
    line-height: 1.3;
    color: var(--sand);
  }

  .cast__summary {
    margin: 0.35rem 0 0;
    font-family: var(--font-label);
    font-size: 0.8125rem;
    line-height: 1.4;
    color: var(--label);
  }

  .cast__open {
    display: inline-flex;
    align-items: center;
    min-block-size: 2rem;
    margin-block-start: 0.5rem;
    font-family: var(--font-label);
    font-weight: 600;
    font-size: 0.6875rem;
    letter-spacing: 0.12em;
    text-transform: uppercase;
    color: var(--label);
    text-decoration: none;
  }

  .cast__open:hover {
    color: var(--sand);
  }

  .cast__open:focus-visible {
    outline: 2px solid var(--amber);
    outline-offset: 2px;
  }

  .cast__retry {
    margin-block-start: 0.75rem;
  }
</style>
