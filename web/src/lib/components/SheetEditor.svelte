<script lang="ts">
  import { ApiError, createApiClient } from "$lib/api";
  import type { SheetDetail } from "$lib/contract/panel.gen";
  import { skillsByRank } from "$lib/sheet";
  import {
    parseInteger,
    parseOptionalInteger,
    patchBody,
    sheetDraft,
    sheetLocked,
    toggleStress,
  } from "$lib/sheet-edit";
  import type { SheetDraft } from "$lib/sheet-edit";

  let {
    slug,
    sheet,
    onupdate,
    onreload,
  }: {
    slug: string;
    sheet: SheetDetail;
    onupdate: (fresh: SheetDetail) => void;
    onreload: () => void;
  } = $props();

  const api = createApiClient();
  let draft = $state<SheetDraft>({
    aspects: [],
    stress: [],
    consequences: [],
    extras: [],
    inventory: [],
    history: "",
    notes: "",
  });
  let saving = $state(false);
  let conflict = $state(false);
  let failure = $state("");
  let notice = $state("");

  const locked = $derived(sheetLocked(sheet, conflict));

  $effect.pre(() => {
    draft = sheetDraft(sheet);
    conflict = false;
  });

  async function save() {
    if (locked || saving) return;
    saving = true;
    failure = "";
    try {
      const fresh = await api.writeSheet(
        slug,
        sheet.id,
        patchBody(sheet, draft),
      );
      onupdate(fresh);
      notice = "Ficha salva.";
    } catch (error) {
      if (error instanceof ApiError && error.status === 409) {
        conflict = true;
      } else if (error instanceof ApiError) {
        failure = error.message;
      } else {
        failure = "Não foi possível salvar a ficha.";
      }
    } finally {
      saving = false;
    }
  }

  function reload() {
    conflict = false;
    failure = "";
    notice = "";
    onreload();
  }
</script>

<div class="sheet__actions">
  <button
    class="hud-btn hud-btn--primary"
    type="button"
    data-testid="sheet-save"
    disabled={locked || saving}
    onclick={save}
  >
    Salvar ficha
  </button>
  <button
    class="hud-btn"
    type="button"
    data-testid="sheet-reload"
    disabled={saving}
    onclick={reload}
  >
    Recarregar
  </button>
  {#if saving}
    <span class="system-note">Salvando…</span>
  {/if}
</div>

{#if conflict}
  <p class="panel-error" role="alert" data-testid="sheet-conflict">
    <span class="stamp is-hazard">Conflito</span>
    <span>
      A ficha mudou no disco. O texto digitado continua aqui; recarregue antes
      de salvar.
    </span>
  </p>
{/if}
{#if failure}
  <p class="panel-error" role="alert" data-testid="sheet-save-error">
    <span class="stamp is-hazard">Hazard</span>
    <span>{failure}</span>
  </p>
{/if}
{#if notice}
  <p class="placard sheet__banner" data-testid="sheet-notice">{notice}</p>
{/if}
{#if sheet.warnings.length}
  <ul class="placard sheet__warnings" data-testid="sheet-warning">
    {#each sheet.warnings as warning (warning)}
      <li>{warning}</li>
    {/each}
  </ul>
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
  <div class="sheet__aspects">
    {#each draft.aspects as aspect, index (index)}
      <label class="sheet__aspect">
        <span class="data-label">{aspect.label}</span>
        <input
          class="hud-input"
          type="text"
          data-testid="sheet-aspect-text"
          bind:value={aspect.text}
          disabled={locked}
        />
      </label>
    {/each}
  </div>
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
  {#each draft.stress as track (track.track)}
    <div class="sheet__track">
      <span class="data-label">{track.track}</span>
      <ol class="sheet__boxes">
        {#each track.boxes as box (box.value)}
          <li>
            <button
              class="sheet__box"
              type="button"
              data-checked={box.checked}
              aria-pressed={box.checked}
              aria-label={`${track.track} ${box.value}${
                box.checked ? " marcada" : " livre"
              }`}
              disabled={locked}
              onclick={() =>
                (draft.stress = toggleStress(draft, track.track, box.value))}
            >
              {box.value}
            </button>
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
  {#each draft.consequences as slot (slot.severity)}
    <label class="sheet__consequence" data-filled={slot.text !== ""}>
      <span class="data-label">{slot.severity} (+{slot.value})</span>
      <input
        class="hud-input"
        type="text"
        data-testid="sheet-consequence-text"
        bind:value={slot.text}
        disabled={locked}
      />
    </label>
  {/each}
</section>

<section
  class="sheet__section"
  aria-labelledby="sheet-extras"
  data-testid="sheet-extras"
>
  <h2 class="panel-label" id="sheet-extras">Extras</h2>
  {#each draft.extras as extra, index (index)}
    <div class="sheet__extra">
      <span class="data-label">{extra.kind}</span>
      <div class="sheet__extra-grid">
        <label class="sheet__field">
          <span class="data-label">Nome</span>
          <input
            class="hud-input"
            type="text"
            data-testid="sheet-extra-name"
            bind:value={extra.name}
            disabled={locked}
          />
        </label>
        <label class="sheet__field">
          <span class="data-label">Texto</span>
          <input
            class="hud-input"
            type="text"
            data-testid="sheet-extra-text"
            bind:value={extra.text}
            disabled={locked}
          />
        </label>
        <label class="sheet__field sheet__field--short">
          <span class="data-label">Custo</span>
          <input
            class="hud-input"
            type="number"
            min="0"
            data-testid="sheet-extra-cost"
            value={extra.cost ?? ""}
            disabled={locked}
            oninput={(event) =>
              (extra.cost = parseOptionalInteger(event.currentTarget.value))}
          />
        </label>
      </div>
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
    {#each draft.inventory as entry, index (index)}
      <li class="sheet__item">
        <label class="sheet__field">
          <span class="data-label">Item</span>
          <input
            class="hud-input"
            type="text"
            data-testid="sheet-inventory-item"
            bind:value={entry.item}
            disabled={locked}
          />
        </label>
        <label class="sheet__field sheet__field--short">
          <span class="data-label">Qtd</span>
          <input
            class="hud-input"
            type="number"
            min="1"
            data-testid="sheet-inventory-qty"
            value={entry.qty}
            disabled={locked}
            oninput={(event) =>
              (entry.qty = parseInteger(event.currentTarget.value, 1))}
          />
        </label>
        <label class="sheet__field">
          <span class="data-label">Nota</span>
          <input
            class="hud-input"
            type="text"
            data-testid="sheet-inventory-note"
            bind:value={entry.note}
            disabled={locked}
          />
        </label>
      </li>
    {:else}
      <li class="system-note">Nenhum item.</li>
    {/each}
  </ul>
</section>

<section
  class="sheet__section"
  aria-labelledby="sheet-history"
  data-testid="sheet-history"
>
  <h2 class="panel-label" id="sheet-history">História</h2>
  <textarea
    class="hud-input sheet__prose"
    data-testid="sheet-prose-history"
    bind:value={draft.history}
    disabled={locked}></textarea>
</section>

<section
  class="sheet__section"
  aria-labelledby="sheet-notes"
  data-testid="sheet-notes"
>
  <h2 class="panel-label" id="sheet-notes">Anotações</h2>
  <textarea
    class="hud-input sheet__prose"
    data-testid="sheet-prose-notes"
    bind:value={draft.notes}
    disabled={locked}></textarea>
</section>

<style>
  .sheet__actions {
    display: flex;
    flex-wrap: wrap;
    align-items: center;
    gap: 0.5rem;
    margin-block-start: 0.85rem;
  }

  .sheet__actions .system-note {
    margin: 0;
  }

  .sheet__banner {
    margin-block-start: 0.85rem;
  }

  .sheet__warnings {
    display: grid;
    gap: 0.25rem;
    margin: 0.85rem 0 0;
    padding-inline-start: 1rem;
    font-family: var(--font-label);
    font-size: 0.75rem;
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
  }

  .sheet__aspect,
  .sheet__field {
    display: grid;
    gap: 0.25rem;
  }

  .sheet__aspect {
    padding-block: 0.4rem;
    border-block-start: 1px solid var(--rule);
  }

  .sheet__aspect:first-child {
    border-block-start: none;
    padding-block-start: 0;
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
    font-family: var(--font-label);
    font-size: 0.6875rem;
    letter-spacing: 0.12em;
    text-transform: uppercase;
    color: var(--amber);
  }

  .sheet__rank-skills {
    font-family: var(--font-value);
    color: var(--sand);
  }

  .sheet__stunt {
    padding-block: 0.4rem;
    border-block-start: 1px solid var(--rule);
  }

  .sheet__stunt:first-of-type {
    border-block-start: none;
  }

  .sheet__stunt-name {
    font-family: var(--font-value);
    color: var(--sand);
  }

  .sheet__stunt-cost {
    margin-inline-start: 0.5rem;
    font-family: var(--font-label);
    font-size: 0.6875rem;
    letter-spacing: 0.1em;
    text-transform: uppercase;
    color: var(--label);
  }

  .sheet__stunt-text {
    margin: 0.25rem 0 0;
    font-family: var(--font-label);
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
    padding: 0;
    border: 1px solid var(--rule-strong);
    border-radius: var(--radius-key);
    font-family: var(--font-value);
    font-size: 0.8125rem;
    color: var(--dim);
    background: var(--sunken);
    cursor: pointer;
  }

  .sheet__box[data-checked="true"] {
    border-color: var(--amber);
    color: var(--amber);
    background: var(--plate-2);
  }

  .sheet__box:disabled {
    cursor: not-allowed;
    opacity: 0.6;
  }

  .sheet__box:focus-visible {
    outline: 2px solid var(--amber);
    outline-offset: 2px;
  }

  .sheet__consequence {
    display: grid;
    grid-template-columns: 9rem minmax(0, 1fr);
    gap: 0.75rem;
    align-items: center;
    padding-block: 0.4rem;
    border-block-start: 1px solid var(--rule);
  }

  .sheet__consequence:first-of-type {
    border-block-start: none;
  }

  .sheet__extra {
    padding-block: 0.4rem;
    border-block-start: 1px solid var(--rule);
  }

  .sheet__extra:first-of-type {
    border-block-start: none;
  }

  .sheet__extra-grid {
    display: grid;
    grid-template-columns: minmax(0, 1fr) minmax(0, 1fr) 5rem;
    gap: 0.5rem;
    margin-block-start: 0.35rem;
  }

  .sheet__inventory {
    display: grid;
    gap: 0.5rem;
    margin: 0;
    padding: 0;
    list-style: none;
  }

  .sheet__item {
    display: grid;
    grid-template-columns: minmax(0, 1fr) 5rem minmax(0, 1fr);
    gap: 0.5rem;
    padding-block: 0.4rem;
    border-block-start: 1px solid var(--rule);
  }

  .sheet__item:first-child {
    border-block-start: none;
  }

  .sheet__prose {
    inline-size: 100%;
    min-block-size: 6rem;
    resize: vertical;
    line-height: 1.5;
  }

  @media (max-width: 30rem) {
    .sheet__consequence,
    .sheet__extra-grid,
    .sheet__item {
      grid-template-columns: minmax(0, 1fr);
    }

    .sheet__field--short {
      max-inline-size: 8rem;
    }
  }
</style>
