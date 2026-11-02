<script lang="ts">
  import { onMount } from "svelte";
  import { resolve } from "$app/paths";
  import { page } from "$app/state";
  import { createApiClient } from "$lib/api";
  import Select from "$lib/components/Select.svelte";
  import { formatCount } from "$lib/format";
  import { phaseForError } from "$lib/phase";
  import type { LoadPhase } from "$lib/phase";
  import {
    sceneCreationNote,
    sceneOriginLabel,
    sceneSavedLabel,
    sceneStateNote,
  } from "$lib/scenes";
  import type { CampaignDetail, SceneSummary } from "$lib/contract/panel.gen";

  const ORIGINS = [
    { id: "image", label: sceneOriginLabel("image") },
    { id: "sketch", label: sceneOriginLabel("sketch") },
  ];

  let phase = $state<LoadPhase>("loading");
  let role = $state<CampaignDetail["role"] | null>(null);
  let cards = $state<SceneSummary[]>([]);
  let composing = $state(false);
  let source = $state<SceneSummary["source"]>("image");
  let draft = $state({ name: "", image: "" });
  let file = $state<File | null>(null);
  let creating = $state(false);
  let failure = $state("");
  let notice = $state("");

  const api = createApiClient();
  const slug = $derived(page.params.campaign ?? "");

  function seedZone() {
    return {
      id: "zon_mapa",
      label: "Mapa",
      revealed: false,
      rects: [{ x: 0, y: 0, w: 1, h: 1 }],
    };
  }

  async function load(campaign: string) {
    phase = "loading";
    try {
      const detail = await api.campaign(campaign);
      role = detail.role;
      cards =
        detail.role === "narrator" ? (await api.scenes(campaign)).scenes : [];
      phase = "ready";
    } catch (error) {
      role = null;
      cards = [];
      phase = phaseForError(error);
    }
  }

  async function create(campaign: string) {
    if (creating) return;
    const name = draft.name.trim();
    if (!name) {
      failure = "Dê um nome à cena.";
      return;
    }
    creating = true;
    failure = "";
    notice = "";
    try {
      const image = await resolveImage(campaign);
      if (source === "image" && image === null) {
        failure = "Escolha uma imagem do vault ou envie uma.";
        return;
      }
      await api.createScene(campaign, {
        name,
        source,
        image,
        zones: [seedZone()],
        fog_outside: true,
      });
      cards = (await api.scenes(campaign)).scenes;
      draft = { name: "", image: "" };
      file = null;
      source = "image";
      composing = false;
      notice = "Cena criada.";
    } catch (error) {
      failure = sceneCreationNote(error);
    } finally {
      creating = false;
    }
  }

  async function resolveImage(campaign: string): Promise<string | null> {
    if (source === "sketch") return null;
    if (file) return (await api.uploadAsset(campaign, file)).path;
    return draft.image.trim() || null;
  }

  function pickFile(event: Event) {
    const input = event.currentTarget as HTMLInputElement;
    file = input.files?.[0] ?? null;
  }

  onMount(() => {
    void load(slug);
  });
</script>

<svelte:head>
  <title>Cenas — Harpi</title>
</svelte:head>

<section class="hud-panel scenes" data-testid="scenes" aria-label="Cenas">
  <div class="panel-band">
    <h1 class="panel-label">Cenas</h1>
    {#if phase === "ready" && role === "narrator"}
      <span class="panel-band__meta">
        {formatCount(cards.length, "cena", "cenas")}
      </span>
    {/if}
  </div>

  {#if phase !== "ready"}
    <p class="system-note" data-testid="scenes-state">
      {sceneStateNote(phase)}
    </p>
    {#if phase === "unavailable" || phase === "failed"}
      <button
        class="hud-btn scenes__retry"
        type="button"
        data-testid="scenes-retry"
        onclick={() => load(slug)}
      >
        Tentar de novo
      </button>
    {/if}
  {:else if role !== "narrator"}
    <p class="system-note" data-testid="scenes-forbidden">
      Só o narrador prepara as cenas.
    </p>
  {:else}
    {#if failure}
      <p class="panel-error" role="alert" data-testid="scenes-error">
        <span class="stamp is-hazard">Hazard</span>
        <span>{failure}</span>
      </p>
    {/if}
    {#if notice}
      <p class="placard scenes__notice" data-testid="scenes-notice">
        {notice}
      </p>
    {/if}

    {#if composing}
      <form
        class="scene-form"
        aria-labelledby="scene-form-label"
        data-testid="scene-form"
        onsubmit={(event) => {
          event.preventDefault();
          void create(slug);
        }}
      >
        <h2 class="panel-label" id="scene-form-label">Nova cena</h2>
        <div class="scene-form__grid">
          <label class="scene-form__field">
            <span class="data-label">Nome</span>
            <input
              class="hud-input"
              type="text"
              maxlength="120"
              required
              data-testid="scene-name"
              bind:value={draft.name}
            />
            <span class="scene-form__hint">O nome vira o arquivo da cena.</span>
          </label>
          <div class="scene-form__field">
            <span class="data-label" id="scene-origin-label">Origem</span>
            <Select
              label="Origem"
              options={ORIGINS}
              value={source}
              testid="scene-origin"
              onchange={(id) => (source = id === "sketch" ? "sketch" : "image")}
            />
          </div>
          {#if source === "image"}
            <label class="scene-form__field scene-form__field--wide">
              <span class="data-label">Imagem do vault</span>
              <input
                class="hud-input"
                type="text"
                placeholder="Harpi/Campaigns/paratheos/assets/…"
                data-testid="scene-image"
                bind:value={draft.image}
              />
            </label>
            <div class="scene-form__field scene-form__field--wide">
              <span class="data-label">Ou envie uma imagem</span>
              <div class="scene-form__upload">
                <label class="hud-btn scene-form__file">
                  <input
                    class="scene-form__file-input"
                    type="file"
                    accept="image/png,image/jpeg,image/webp"
                    data-testid="scene-upload"
                    onchange={pickFile}
                  />
                  Escolher imagem
                </label>
                <span class="scene-form__hint" data-testid="scene-file">
                  {file ? file.name : "Nenhum arquivo escolhido"}
                </span>
              </div>
            </div>
          {:else}
            <p class="system-note scene-form__field--wide">
              A cena nasce sem imagem externa. As salas desenhadas viram as
              áreas de névoa.
            </p>
          {/if}
        </div>
        <div class="scene-form__actions">
          <button
            class="hud-btn hud-btn--primary"
            type="submit"
            data-testid="scene-submit"
            disabled={creating}
          >
            {creating ? "Criando…" : "Criar cena"}
          </button>
          <button
            class="hud-btn"
            type="button"
            data-testid="scene-cancel"
            disabled={creating}
            onclick={() => (composing = false)}
          >
            Cancelar
          </button>
        </div>
      </form>
    {/if}

    <ul class="gallery" data-testid="scene-gallery">
      {#each cards as card (card.slug)}
        <li
          class="gallery__card"
          data-testid="scene-card"
          data-slug={card.slug}
        >
          <div class="gallery__thumb">
            {#if card.thumbnail}
              <img src={card.thumbnail} alt="" loading="lazy" />
            {:else if card.zones.some((zone) => zone.rects.length > 0)}
              <svg
                class="gallery__preview"
                viewBox={`0 0 ${card.width} ${card.height}`}
                role="img"
                aria-label={`Mapa de ${card.name}`}
                preserveAspectRatio="xMidYMid meet"
              >
                {#each card.zones as zone (zone.id)}
                  {#each zone.rects as rect, index (`${zone.id}-${index}`)}
                    <rect
                      class="gallery__zone"
                      data-revealed={zone.revealed}
                      x={rect.x * card.grid.cell_px + card.grid.offset_x}
                      y={rect.y * card.grid.cell_px + card.grid.offset_y}
                      width={rect.w * card.grid.cell_px}
                      height={rect.h * card.grid.cell_px}
                    />
                  {/each}
                {/each}
              </svg>
            {:else}
              <span class="gallery__hatch" aria-hidden="true"></span>
            {/if}
          </div>
          <div class="gallery__body">
            <h2 class="gallery__name">
              <a
                class="gallery__open"
                href={resolve("/c/[campaign]/cenas/[scene]", {
                  campaign: slug,
                  scene: card.slug,
                })}
                data-testid="scene-open"
              >
                {card.name}
              </a>
            </h2>
            <dl class="gallery__facts">
              <div class="gallery__fact">
                <dt class="data-label">Origem</dt>
                <dd class="data-value">{sceneOriginLabel(card.source)}</dd>
              </div>
              <div class="gallery__fact">
                <dt class="data-label">Áreas</dt>
                <dd class="data-value">{card.zone_count}</dd>
              </div>
            </dl>
            <div class="gallery__states">
              <span
                class="gallery__state"
                data-saved={card.saved}
                data-testid="scene-saved"
              >
                {sceneSavedLabel(card.saved)}
              </span>
              {#if card.in_use}
                <span class="gallery__badge" data-testid="scene-in-use">
                  Em mesa
                </span>
              {/if}
            </div>
          </div>
        </li>
      {/each}
      <li class="gallery__card gallery__card--new">
        <button
          class="gallery__new"
          type="button"
          data-testid="scene-new"
          onclick={() => (composing = true)}
        >
          <span class="gallery__plus" aria-hidden="true">+</span>
          <span class="gallery__new-label">Nova cena</span>
        </button>
      </li>
    </ul>
  {/if}
</section>

<style>
  .scenes__retry {
    margin-block-start: 0.75rem;
  }

  .scenes__notice {
    margin-block-start: 0.85rem;
    font-family: var(--font-label);
    font-size: 0.6875rem;
    letter-spacing: 0.12em;
    text-transform: uppercase;
    color: var(--amber);
  }

  .scene-form {
    margin-block-end: 1rem;
    padding-block-end: 0.85rem;
    border-block-end: 1px solid var(--rule);
  }

  .scene-form__grid {
    display: grid;
    gap: 0.5rem;
  }

  .scene-form__field {
    display: grid;
    gap: 0.25rem;
  }

  .scene-form__hint {
    font-family: var(--font-value);
    font-size: 0.75rem;
    color: var(--faint);
  }

  .scene-form__upload {
    display: flex;
    flex-wrap: wrap;
    align-items: center;
    gap: 0.5rem;
  }

  .scene-form__file {
    position: relative;
    display: inline-flex;
    align-items: center;
    overflow: hidden;
    cursor: pointer;
  }

  .scene-form__file-input {
    position: absolute;
    inset: 0;
    opacity: 0;
    cursor: pointer;
  }

  .scene-form__file:focus-within {
    outline: 2px solid var(--amber);
    outline-offset: 2px;
  }

  .scene-form__actions {
    display: flex;
    flex-wrap: wrap;
    align-items: center;
    gap: 0.5rem;
    margin-block-start: 0.75rem;
  }

  .gallery {
    display: grid;
    grid-template-columns: repeat(auto-fill, minmax(min(100%, 12rem), 1fr));
    gap: 0.75rem;
    margin: 0;
    padding: 0;
    list-style: none;
  }

  .gallery__card {
    display: flex;
    flex-direction: column;
    border: 1px solid var(--rule-strong);
    border-radius: var(--radius-plate);
    background: var(--plate-2);
    overflow: hidden;
  }

  .gallery__thumb {
    display: grid;
    place-items: center;
    aspect-ratio: 4 / 3;
    background: var(--sunken);
    border-block-end: 1px solid var(--rule);
  }

  .gallery__thumb img {
    display: block;
    inline-size: 100%;
    block-size: 100%;
    object-fit: cover;
  }

  .gallery__hatch {
    display: block;
    inline-size: 100%;
    block-size: 100%;
    background: repeating-linear-gradient(
      45deg,
      var(--rule-strong) 0 1px,
      transparent 1px 9px
    );
  }

  .gallery__preview {
    display: block;
    inline-size: 100%;
    block-size: 100%;
    background: var(--sunken);
  }

  .gallery__zone {
    fill: var(--plate);
    stroke: var(--rule-strong);
    stroke-width: 1;
  }

  .gallery__zone[data-revealed="true"] {
    fill: var(--amber);
  }

  .gallery__body {
    display: grid;
    gap: 0.5rem;
    padding: 0.65rem 0.7rem 0.75rem;
  }

  .gallery__name {
    margin: 0;
    font-family: var(--font-display);
    font-weight: 700;
    font-size: 1rem;
    line-height: 1.15;
    color: var(--sand);
  }

  .gallery__open {
    color: inherit;
    text-decoration: none;
    border-radius: var(--radius-key);
  }

  .gallery__open:hover {
    color: var(--amber);
  }

  .gallery__open:focus-visible {
    outline: 2px solid var(--amber);
    outline-offset: 2px;
  }

  .gallery__facts {
    display: flex;
    flex-wrap: wrap;
    gap: 0.35rem 2rem;
    margin: 0;
  }

  .gallery__fact {
    display: grid;
    gap: 0.15rem;
  }

  .gallery__fact dd {
    margin: 0;
  }

  .gallery__states {
    display: flex;
    flex-wrap: wrap;
    align-items: center;
    gap: 0.5rem;
    font-family: var(--font-label);
    font-weight: 600;
    font-size: 0.6875rem;
    letter-spacing: 0.12em;
    text-transform: uppercase;
  }

  .gallery__state {
    color: var(--amber);
  }

  .gallery__state[data-saved="false"] {
    color: var(--oxide);
  }

  .gallery__badge {
    padding: 0.15rem 0.4rem;
    border: 1px solid var(--amber);
    border-radius: 2px;
    color: var(--amber);
  }

  .gallery__card--new {
    background: transparent;
  }

  .gallery__new {
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    gap: 0.5rem;
    inline-size: 100%;
    block-size: 100%;
    min-block-size: 10rem;
    padding: 0.75rem;
    border: none;
    background: transparent;
    color: var(--label);
    cursor: pointer;
  }

  .gallery__new:hover {
    color: var(--sand);
  }

  .gallery__new:focus-visible {
    outline: 2px solid var(--amber);
    outline-offset: -4px;
  }

  .gallery__plus {
    font-family: var(--font-display);
    font-weight: 800;
    font-size: 1.5rem;
    line-height: 1;
  }

  .gallery__new-label {
    font-family: var(--font-label);
    font-weight: 600;
    font-size: 0.6875rem;
    letter-spacing: 0.14em;
    text-transform: uppercase;
  }

  @media (min-width: 48rem) {
    .scene-form__grid {
      grid-template-columns: minmax(0, 1fr) minmax(0, 1fr);
    }

    .scene-form__field--wide {
      grid-column: 1 / -1;
    }
  }
</style>
