<script lang="ts">
  import { onMount } from "svelte";
  import { resolve } from "$app/paths";
  import { page } from "$app/state";
  import { createApiClient } from "$lib/api";
  import {
    approvalOwner,
    castInitials,
    castStateNote,
    creationNote,
    decisionNote,
  } from "$lib/cast";
  import { conflictLabel } from "$lib/conflicts";
  import { formatCount } from "$lib/format";
  import { phaseForError } from "$lib/phase";
  import type { LoadPhase } from "$lib/phase";
  import type {
    ApprovalItem,
    CampaignDetail,
    CharacterCard,
    SheetConflictField,
    SheetNoticeItem,
  } from "$lib/contract/panel.gen";

  let phase = $state<LoadPhase>("loading");
  let role = $state<CampaignDetail["role"] | null>(null);
  let cards = $state<CharacterCard[]>([]);
  let own = $state<string | null>(null);
  let queue = $state<ApprovalItem[]>([]);
  let conflicts = $state<SheetConflictField[]>([]);
  let notices = $state<SheetNoticeItem[]>([]);
  let draft = $state({ name: "", concept: "", summary: "" });
  let withSheet = $state(false);
  let notes = $state<Record<string, string>>({});
  let busy = $state<string | null>(null);
  let creating = $state(false);
  let failure = $state("");
  let notice = $state("");

  const api = createApiClient();
  const slug = $derived(page.params.campaign ?? "");

  async function load(campaign: string) {
    phase = "loading";
    try {
      const [detail, cast] = await Promise.all([
        api.campaign(campaign),
        api.campaignCharacters(campaign),
      ]);
      role = detail.role;
      cards = cast.characters;
      own = cast.own_character_id;
      queue =
        detail.role === "narrator"
          ? (await api.approvals(campaign)).approvals
          : [];
      conflicts =
        detail.role === "narrator"
          ? (await api.conflicts(campaign)).conflicts
          : [];
      notices = (await api.notices(campaign)).notices;
      phase = "ready";
    } catch (error) {
      role = null;
      cards = [];
      queue = [];
      conflicts = [];
      notices = [];
      phase = phaseForError(error);
    }
  }

  async function create(campaign: string) {
    if (creating) return;
    const name = draft.name.trim();
    if (!name) {
      failure = "Dê um nome ao personagem.";
      return;
    }
    creating = true;
    failure = "";
    notice = "";
    try {
      const npc = role === "narrator";
      const detail = await api.createCharacter(campaign, {
        name,
        concept: draft.concept.trim() || null,
        summary: draft.summary.trim() || null,
        sheet: npc ? withSheet : undefined,
      });
      draft = { name: "", concept: "", summary: "" };
      withSheet = false;
      notice = npc ? "NPC criado." : "Personagem enviado para aprovação.";
      if (!npc) own = detail.card.id;
      cards = (await api.campaignCharacters(campaign)).characters;
    } catch (error) {
      failure = creationNote(error);
    } finally {
      creating = false;
    }
  }

  async function decide(
    campaign: string,
    item: ApprovalItem,
    decision: "approve" | "reject",
  ) {
    const note = (notes[item.id] ?? "").trim();
    if (decision === "reject" && !note) {
      failure = "Escreva a nota da recusa.";
      return;
    }
    busy = item.id;
    failure = "";
    notice = "";
    try {
      queue = (await api.decideApproval(campaign, item.id, { decision, note }))
        .approvals;
      notice = decision === "approve" ? "Ficha aprovada." : "Ficha devolvida.";
      cards = (await api.campaignCharacters(campaign)).characters;
    } catch (error) {
      failure = decisionNote(error);
    } finally {
      busy = null;
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
  {:else}
    {#if failure}
      <p class="panel-error" role="alert" data-testid="cast-error">
        <span class="stamp is-hazard">Hazard</span>
        <span>{failure}</span>
      </p>
    {/if}
    {#if notice}
      <p class="placard cast__notice" data-testid="cast-notice">{notice}</p>
    {/if}

    {#if role === "narrator"}
      <section
        class="queue"
        aria-labelledby="approval-queue-label"
        data-testid="approval-queue"
      >
        <h2 class="panel-label" id="approval-queue-label">Fila de aprovação</h2>
        {#if queue.length === 0}
          <p class="system-note" data-testid="approval-empty">
            Nenhuma ficha aguardando aprovação.
          </p>
        {:else}
          <ul class="queue__list">
            {#each queue as item (item.id)}
              <li class="queue__item" data-testid="approval-item">
                <div class="queue__head">
                  <h3 class="queue__name">{item.character_name}</h3>
                  <span class="queue__owner">{approvalOwner(item)}</span>
                  {#if item.character_id}
                    <a
                      class="queue__open"
                      href={resolve("/c/[campaign]/ficha/[[character]]", {
                        campaign: slug,
                        character: item.character_id,
                      })}
                      data-testid="approval-open"
                    >
                      Abrir ficha
                    </a>
                  {/if}
                </div>
                <label class="queue__note">
                  <span class="data-label">Nota da recusa</span>
                  <textarea
                    class="hud-input queue__note-input"
                    rows="2"
                    data-testid="approval-note"
                    value={notes[item.id] ?? ""}
                    oninput={(event) =>
                      (notes[item.id] = event.currentTarget.value)}></textarea>
                </label>
                <div class="queue__actions">
                  <button
                    class="hud-btn hud-btn--primary"
                    type="button"
                    data-testid="approval-approve"
                    disabled={busy !== null}
                    onclick={() => decide(slug, item, "approve")}
                  >
                    Aprovar
                  </button>
                  <button
                    class="hud-btn hud-btn-danger"
                    type="button"
                    data-testid="approval-reject"
                    disabled={busy !== null || !(notes[item.id] ?? "").trim()}
                    onclick={() => decide(slug, item, "reject")}
                  >
                    Recusar
                  </button>
                </div>
              </li>
            {/each}
          </ul>
        {/if}
      </section>
    {/if}

    {#if notices.length > 0}
      <section
        class="queue"
        aria-labelledby="sheet-notices-label"
        data-testid="sheet-notices"
      >
        <h2 class="panel-label" id="sheet-notices-label">Avisos</h2>
        <ul class="queue__list">
          {#each notices as notice (notice.id)}
            <li class="queue__item" data-testid="sheet-notice">
              <div class="queue__head">
                <h3 class="queue__name">{notice.name}</h3>
                <span class="queue__owner">
                  {notice.title}
                </span>
                {#if notice.character_id}
                  <a
                    class="queue__open"
                    href={resolve("/c/[campaign]/ficha/[[character]]", {
                      campaign: slug,
                      character: notice.character_id,
                    })}
                    data-testid="sheet-notice-open"
                  >
                    Abrir ficha
                  </a>
                {/if}
              </div>
              {#if notice.fields.length > 0}
                <p class="system-note" data-testid="sheet-notice-fields">
                  {notice.fields.map(conflictLabel).join(" · ")}
                </p>
              {/if}
            </li>
          {/each}
        </ul>
      </section>
    {/if}

    {#if role === "narrator"}
      <section
        class="queue"
        aria-labelledby="conflict-summary-label"
        data-testid="conflict-summary"
      >
        <h2 class="panel-label" id="conflict-summary-label">
          Fila de conflitos
        </h2>
        {#if conflicts.length === 0}
          <p class="system-note" data-testid="conflict-summary-empty">
            Nenhum campo em conflito.
          </p>
        {:else}
          <ul class="queue__list">
            {#each conflicts as conflict (conflict.id)}
              <li class="queue__item" data-testid="conflict-summary-item">
                <div class="queue__head">
                  <h3 class="queue__name">
                    {conflictLabel(conflict.field_path)}
                  </h3>
                  <span class="queue__owner">{conflict.sheet_id}</span>
                  {#if conflict.character_id}
                    <a
                      class="queue__open"
                      href={resolve("/c/[campaign]/ficha/[[character]]", {
                        campaign: slug,
                        character: conflict.character_id,
                      })}
                      data-testid="conflict-summary-open"
                    >
                      Abrir ficha
                    </a>
                  {/if}
                </div>
              </li>
            {/each}
          </ul>
        {/if}
      </section>
    {/if}

    {#if role === "narrator" || (role === "pending" && !own)}
      <form
        class="create"
        aria-labelledby="character-create-label"
        data-testid="character-create"
        onsubmit={(event) => {
          event.preventDefault();
          void create(slug);
        }}
      >
        <h2 class="panel-label" id="character-create-label">
          {role === "narrator" ? "Novo NPC" : "Novo personagem"}
        </h2>
        <div class="create__grid">
          <label class="create__field">
            <span class="data-label">Nome</span>
            <input
              class="hud-input"
              type="text"
              maxlength="80"
              required
              data-testid="character-name"
              bind:value={draft.name}
            />
          </label>
          <label class="create__field">
            <span class="data-label">Conceito</span>
            <input
              class="hud-input"
              type="text"
              data-testid="character-concept"
              bind:value={draft.concept}
            />
          </label>
          <label class="create__field create__field--wide">
            <span class="data-label">Resumo</span>
            <textarea
              class="hud-input create__summary"
              rows="3"
              data-testid="character-summary"
              bind:value={draft.summary}></textarea>
          </label>
        </div>
        {#if role === "narrator"}
          <label class="create__check">
            <input
              type="checkbox"
              data-testid="character-with-sheet"
              bind:checked={withSheet}
            />
            <span class="data-label">Criar ficha</span>
          </label>
        {/if}
        <div class="create__actions">
          <button
            class="hud-btn hud-btn--primary"
            type="submit"
            data-testid="character-submit"
            disabled={creating}
          >
            {role === "narrator" ? "Criar NPC" : "Criar personagem"}
          </button>
          {#if creating}
            <span class="system-note">Enviando…</span>
          {/if}
        </div>
      </form>
    {:else if role === "pending" && own}
      <p class="placard cast__notice" data-testid="cast-pending">
        Personagem em análise pelo narrador.
      </p>
    {/if}

    {#if cards.length === 0}
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

  .cast__notice {
    margin-block-start: 0.85rem;
    font-family: var(--font-label);
    font-size: 0.6875rem;
    letter-spacing: 0.12em;
    text-transform: uppercase;
    color: var(--amber);
  }

  .queue {
    margin-block-end: 1rem;
  }

  .queue .panel-label {
    margin-block-end: 0.5rem;
  }

  .queue__list {
    margin: 0;
    padding: 0;
    list-style: none;
  }

  .queue__item {
    padding-block: 0.75rem;
    border-block-start: 1px solid var(--rule);
  }

  .queue__head {
    display: flex;
    flex-wrap: wrap;
    align-items: baseline;
    gap: 0.6rem;
  }

  .queue__name {
    margin: 0;
    font-family: var(--font-display);
    font-weight: 700;
    font-size: 1.125rem;
    color: var(--sand);
  }

  .queue__owner {
    font-family: var(--font-value);
    font-size: 0.75rem;
    color: var(--dim);
  }

  .queue__open {
    display: inline-flex;
    align-items: center;
    min-block-size: 2rem;
    margin-inline-start: auto;
    font-family: var(--font-label);
    font-weight: 600;
    font-size: 0.6875rem;
    letter-spacing: 0.12em;
    text-transform: uppercase;
    color: var(--label);
    text-decoration: none;
  }

  .queue__open:hover {
    color: var(--sand);
  }

  .queue__open:focus-visible {
    outline: 2px solid var(--amber);
    outline-offset: 2px;
  }

  .queue__note {
    display: grid;
    gap: 0.25rem;
    margin-block-start: 0.5rem;
  }

  .queue__note-input {
    inline-size: 100%;
    min-block-size: 3.5rem;
    resize: vertical;
  }

  .queue__actions {
    display: flex;
    flex-wrap: wrap;
    gap: 0.5rem;
    margin-block-start: 0.5rem;
  }

  .create {
    margin-block-end: 1rem;
    padding-block-end: 0.85rem;
    border-block-end: 1px solid var(--rule);
  }

  .create__grid {
    display: grid;
    gap: 0.5rem;
  }

  .create__field {
    display: grid;
    gap: 0.25rem;
  }

  .create__summary {
    inline-size: 100%;
    min-block-size: 4rem;
    resize: vertical;
  }

  .create__check {
    display: flex;
    align-items: center;
    gap: 0.5rem;
    min-block-size: 2.5rem;
    margin-block-start: 0.5rem;
  }

  .create__check input {
    accent-color: var(--amber);
  }

  .create__actions {
    display: flex;
    flex-wrap: wrap;
    align-items: center;
    gap: 0.5rem;
    margin-block-start: 0.75rem;
  }

  .create__actions .system-note {
    margin: 0;
  }

  @media (min-width: 48rem) {
    .create__grid {
      grid-template-columns: minmax(0, 1fr) minmax(0, 1fr);
    }

    .create__field--wide {
      grid-column: 1 / -1;
    }
  }
</style>
