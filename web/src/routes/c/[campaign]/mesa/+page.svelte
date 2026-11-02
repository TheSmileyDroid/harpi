<script lang="ts">
  import { onMount } from "svelte";
  import { resolve } from "$app/paths";
  import { page } from "$app/state";
  import { ApiError, createApiClient } from "$lib/api";
  import SheetEditor from "$lib/components/SheetEditor.svelte";
  import TableMap from "$lib/components/TableMap.svelte";
  import { phaseForError } from "$lib/phase";
  import type { LoadPhase } from "$lib/phase";
  import {
    tableActionNote,
    tableOpenNote,
    tableRoleLabel,
    tableRoundLabel,
    tableSpectatorsLabel,
    tableStateNote,
    tableTokenNote,
    tableZoneNote,
  } from "$lib/tables";
  import type {
    SceneZone,
    SceneSummary,
    TableScene,
    TableSummary,
    TableToken,
    CharacterDetail,
    SheetDetail,
  } from "$lib/contract/panel.gen";

  const api = createApiClient();
  const slug = $derived(page.params.campaign ?? "");
  const queryTable = $derived(page.url.searchParams.get("table") ?? "");

  let phase = $state<LoadPhase>("loading");
  let table = $state<TableSummary | null>(null);
  let campaignRole = $state<TableSummary["role"] | null>(null);
  let cards = $state<SceneSummary[]>([]);
  let busy = $state("");
  let failure = $state("");
  let notice = $state("");
  let warning = $state("");

  let openDraft = $state({ scene: "", channel: "", name: "" });
  let sceneDraft = $state("");
  let tokenDraft = $state({
    label: "",
    x: "0",
    y: "0",
    w: "1",
    h: "1",
    owner: "",
    character: "",
    color: "#e9dfc7",
    visible: true,
  });
  let selectedId = $state<string | null>(null);

  let drawerOpen = $state(false);
  let character = $state<CharacterDetail | null>(null);
  let drawerLoading = $state(false);
  let drawerFailure = $state("");

  const viewerRole = $derived(table?.role ?? campaignRole);
  const narrator = $derived(viewerRole === "narrator");
  const pending = $derived(viewerRole === "pending");
  const spectator = $derived(viewerRole === "spectator");
  const scene = $derived<TableScene | null>(table?.scene ?? null);
  const sceneChanged = $derived(
    table?.role === "narrator" &&
      table.status === "open" &&
      table.scene !== null &&
      !table.scene.saved,
  );
  const selected = $derived<TableToken | null>(
    table?.tokens.find((token) => token.id === selectedId) ?? null,
  );

  async function load(campaign: string, directTable: string) {
    phase = "loading";
    table = null;
    cards = [];
    try {
      if (directTable) {
        table = await api.tableSummary(directTable);
        campaignRole = table.role;
        sceneDraft = table.scene?.slug ?? "";
        phase = "ready";
        return;
      }
      const detail = await api.campaign(campaign);
      campaignRole = detail.role;
      cards =
        detail.role === "narrator" ? (await api.scenes(campaign)).scenes : [];
      const first = cards[0];
      if (first) openDraft.scene = first.slug;
      if (detail.open_table) {
        table = await api.tableSummary(detail.open_table.id);
      }
      sceneDraft = table?.scene?.slug ?? "";
      phase = "ready";
    } catch (error) {
      phase = phaseForError(error);
    }
  }

  onMount(() => {
    void load(slug, queryTable);
  });

  $effect(() => {
    function onKey(event: KeyboardEvent) {
      if (event.key === "Escape" && drawerOpen) {
        closeDrawer();
      }
    }
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  });

  async function act(name: string, work: () => Promise<void>) {
    if (busy) return;
    busy = name;
    failure = "";
    notice = "";
    try {
      await work();
    } finally {
      busy = "";
    }
  }

  async function openTable() {
    if (!openDraft.scene) {
      failure = "Escolha uma cena.";
      return;
    }
    if (!openDraft.channel.trim()) {
      failure = "Informe o canal de texto da sessão.";
      return;
    }
    await act("open", async () => {
      try {
        table = await api.openTable({
          campaign: slug,
          channel_id: openDraft.channel.trim(),
          scene: openDraft.scene,
          name: openDraft.name.trim() || null,
        });
        sceneDraft = table.scene?.slug ?? "";
        selectedId = null;
        notice = "Mesa aberta.";
      } catch (error) {
        if (error instanceof ApiError && error.code === "table_already_open") {
          failure = await activeTableNote();
        } else {
          failure = tableOpenNote(error);
        }
      }
    });
  }

  async function activeTableNote(): Promise<string> {
    const fallback = "Já existe uma mesa aberta nesta campanha ou neste canal.";
    try {
      const detail = await api.campaign(slug);
      const active = detail.open_table;
      if (active) {
        return `A mesa "${active.name}" (${active.id}) já está aberta no canal ${active.channel_id}.`;
      }
    } catch {
      return fallback;
    }
    return fallback;
  }

  async function closeTable() {
    if (!table) return;
    await act("close", async () => {
      try {
        table = await api.closeTable(table!.id);
        warning = "";
        selectedId = null;
        notice = "Mesa fechada. Snapshot gravado.";
      } catch (error) {
        failure = tableActionNote(error);
      }
    });
  }

  async function reopenTable() {
    if (!table) return;
    await act("reopen", async () => {
      try {
        table = await api.reopenTable(table!.id);
        warning = table.warning ?? "";
        sceneDraft = table.scene?.slug ?? "";
        notice = "Mesa reaberta.";
      } catch (error) {
        failure = tableActionNote(error);
      }
    });
  }

  async function changeScene(sceneSlug: string) {
    if (!table || !sceneSlug) return;
    await act("scene", async () => {
      try {
        table = await api.changeTableScene(table!.id, {
          scene: sceneSlug,
        });
        selectedId = null;
        notice = "Cena trocada.";
      } catch (error) {
        failure = tableActionNote(error);
      }
    });
  }

  async function reloadScene() {
    if (!table) return;
    await act("reload", async () => {
      try {
        table = await api.reloadTableScene(table!.id);
        warning = table.warning ?? "";
        notice = "Cena recarregada do disco.";
      } catch (error) {
        failure = tableActionNote(error);
      }
    });
  }

  async function toggleZone(zone: SceneZone) {
    if (!table || !narrator) return;
    await act(`zone-${zone.id}`, async () => {
      try {
        table = zone.revealed
          ? await api.hideZone(table!.id, zone.id)
          : await api.revealZone(table!.id, zone.id);
        notice = zone.revealed ? "Área coberta." : "Área revelada.";
      } catch (error) {
        failure = tableZoneNote(error);
      }
    });
  }

  async function moveToken(token: TableToken, x: number, y: number) {
    if (!table || !narrator) return;
    await act("move", async () => {
      try {
        table = await api.patchTableToken(table!.id, token.id, { x, y });
      } catch (error) {
        failure = tableTokenNote(error);
      }
    });
  }

  async function createToken() {
    if (!table || !narrator) return;
    const x = Number(tokenDraft.x);
    const y = Number(tokenDraft.y);
    const w = Number(tokenDraft.w);
    const h = Number(tokenDraft.h);
    if (!tokenDraft.label.trim()) {
      failure = "Dê um rótulo ao token.";
      return;
    }
    if (![x, y, w, h].every((value) => Number.isFinite(value))) {
      failure = "Confira a posição e o tamanho do token.";
      return;
    }
    await act("token", async () => {
      try {
        table = await api.createTableToken(table!.id, {
          label: tokenDraft.label.trim(),
          x,
          y,
          w,
          h,
          ...(tokenDraft.owner.trim()
            ? { owner_id: tokenDraft.owner.trim() }
            : {}),
          ...(tokenDraft.character.trim()
            ? { character_id: tokenDraft.character.trim() }
            : {}),
          color: tokenDraft.color,
          visible: tokenDraft.visible,
        });
        tokenDraft = {
          label: "",
          x: "0",
          y: "0",
          w: "1",
          h: "1",
          owner: "",
          character: "",
          color: "#e9dfc7",
          visible: true,
        };
        notice = "Token criado.";
      } catch (error) {
        failure = tableTokenNote(error);
      }
    });
  }

  async function toggleTokenVisibility(token: TableToken) {
    if (!table || !narrator) return;
    await act("visibility", async () => {
      try {
        table = await api.patchTableToken(table!.id, token.id, {
          visible: !token.visible,
        });
      } catch (error) {
        failure = tableTokenNote(error);
      }
    });
  }

  async function removeToken(token: TableToken) {
    if (!table || !narrator) return;
    await act("remove", async () => {
      try {
        table = await api.deleteTableToken(table!.id, token.id);
        if (selectedId === token.id) {
          selectedId = null;
          closeDrawer();
        }
        notice = "Token removido.";
      } catch (error) {
        failure = tableTokenNote(error);
      }
    });
  }

  async function toggleSpectators() {
    if (!table || !narrator) return;
    await act("spectators", async () => {
      try {
        table = await api.setTableSpectators(table!.id, {
          enabled: !table!.spectators,
        });
      } catch (error) {
        failure = tableActionNote(error);
      }
    });
  }

  async function openToken(token: TableToken) {
    selectedId = token.id;
    drawerOpen = true;
    character = null;
    drawerFailure = "";
    if (!token.character_id) return;
    drawerLoading = true;
    try {
      character = await api.campaignCharacter(slug, token.character_id);
    } catch (error) {
      drawerFailure =
        error instanceof ApiError && error.status === 404
          ? "O personagem deste token não está visível."
          : "Não foi possível abrir a ficha.";
    } finally {
      drawerLoading = false;
    }
  }

  function closeDrawer() {
    drawerOpen = false;
    character = null;
    drawerFailure = "";
  }

  function updateSheet(fresh: SheetDetail) {
    if (character?.kind === "sheet") {
      character = { ...character, sheet: fresh };
    }
  }

  function reloadSheet() {
    const token = selected;
    if (token) void openToken(token);
  }
</script>

<svelte:head>
  <title>Mesa — Harpi</title>
</svelte:head>

<section class="hud-panel table" data-testid="table" aria-label="Mesa">
  <div class="panel-band">
    <h1 class="panel-label">Mesa</h1>
    {#if table}
      <span class="panel-band__meta" data-testid="table-round">
        {tableRoundLabel(table.round)}
      </span>
    {/if}
  </div>

  {#if phase !== "ready"}
    <p class="system-note" data-testid="table-state">
      {tableStateNote(phase)}
    </p>
    {#if phase === "unavailable" || phase === "failed"}
      <button
        class="hud-btn table__retry"
        type="button"
        data-testid="table-retry"
        onclick={() => load(slug, queryTable)}
      >
        Tentar de novo
      </button>
    {/if}
  {:else if pending}
    <p class="placard table__banner" data-testid="table-pending">
      Sua ficha está pendente. Você acompanha a mesa, mas não conduz.
      <a
        class="table__link"
        href={resolve("/c/[campaign]/personagens", { campaign: slug })}
      >
        Como entrar
      </a>
    </p>
  {:else if spectator}
    <p class="placard table__banner" data-testid="table-spectator">
      Visão de espectador. Você vê a mesa, sem ficha e sem conduzir.
    </p>
  {/if}

  {#if phase === "ready" && table}
    {#if failure}
      <p class="panel-error" role="alert" data-testid="table-error">
        <span class="stamp is-hazard">Hazard</span>
        <span>{failure}</span>
      </p>
    {/if}
    {#if notice}
      <p class="placard table__notice" data-testid="table-notice">
        {notice}
      </p>
    {/if}
    {#if warning}
      <p class="panel-error" role="alert" data-testid="table-warning">
        <span class="stamp is-hazard">Aviso</span>
        <span>{warning}</span>
      </p>
    {/if}
    {#if sceneChanged}
      <p class="placard table__notice" data-testid="table-scene-changed">
        A cena mudou no disco. O narrador precisa recarregar a cena.
      </p>
    {/if}

    <div class="table__placards">
      <span class="placard table__placard">
        <span class="placard__label">Papel</span>
        <span class="placard__value" data-testid="table-role">
          {tableRoleLabel(table.role)}
        </span>
      </span>
      <span class="placard table__placard">
        <span class="placard__label">Estado</span>
        <span class="placard__value" data-testid="table-status">
          {table.status === "open" ? "Aberta" : "Fechada"}
        </span>
      </span>
      <span class="placard table__placard">
        <span class="placard__label">Canal</span>
        <span class="placard__value" data-testid="table-channel">
          {table.channel_id}
        </span>
      </span>
      <span class="placard table__placard">
        <span class="placard__label">Espectadores</span>
        <span class="placard__value" data-testid="table-spectators">
          {tableSpectatorsLabel(table.spectators)}
        </span>
      </span>
    </div>

    <div class="table__body" data-testid="table-summary">
      <div class="table__stage">
        {#if scene}
          <TableMap
            {scene}
            tokens={table.tokens}
            role={table.role}
            viewerId={table.viewer_id}
            {selectedId}
            ontoken={openToken}
            onzone={toggleZone}
            onmove={moveToken}
          />
        {:else}
          <p class="system-note">A mesa ainda não tem uma cena corrente.</p>
        {/if}
      </div>

      <aside class="table__column" aria-label="Condução da mesa">
        {#if narrator}
          <section class="table__panel" data-testid="table-conduct">
            <h2 class="panel-label">Condução</h2>
            {#if table.status === "open"}
              <div class="table__field">
                <label class="data-label" for="table-scene">Cena</label>
                <select
                  class="hud-input"
                  id="table-scene"
                  data-testid="table-scene-select"
                  bind:value={sceneDraft}
                >
                  {#each cards as card (card.slug)}
                    <option value={card.slug}>{card.name}</option>
                  {/each}
                </select>
              </div>
              <div class="table__keys">
                <button
                  class="hud-btn"
                  type="button"
                  data-testid="table-scene-change"
                  disabled={busy !== "" || !sceneDraft}
                  onclick={() => changeScene(sceneDraft)}
                >
                  Trocar cena
                </button>
                <button
                  class="hud-btn"
                  type="button"
                  data-testid="table-scene-reload"
                  disabled={busy !== ""}
                  onclick={reloadScene}
                >
                  Recarregar cena
                </button>
              </div>
              <div class="table__keys">
                <button
                  class="hud-btn hud-btn-danger"
                  type="button"
                  data-testid="table-close"
                  disabled={busy !== ""}
                  onclick={closeTable}
                >
                  Fechar mesa
                </button>
                <button
                  class="hud-btn"
                  type="button"
                  data-testid="table-spectator-toggle"
                  disabled={busy !== ""}
                  onclick={toggleSpectators}
                >
                  {table.spectators
                    ? "Fechar espectadores"
                    : "Abrir espectadores"}
                </button>
              </div>
            {:else}
              <p class="system-note">
                A mesa está fechada. O snapshot guardou a cena, a névoa, os
                tokens e a rodada.
              </p>
              <button
                class="hud-btn hud-btn--primary"
                type="button"
                data-testid="table-reopen"
                disabled={busy !== ""}
                onclick={reopenTable}
              >
                Reabrir mesa
              </button>
            {/if}
          </section>

          {#if table.status === "open"}
            <section class="table__panel" data-testid="table-token-form">
              <h2 class="panel-label">Novo token</h2>
              <div class="table__grid">
                <label class="table__field table__field--wide">
                  <span class="data-label">Rótulo</span>
                  <input
                    class="hud-input"
                    type="text"
                    maxlength="120"
                    data-testid="table-token-label"
                    bind:value={tokenDraft.label}
                  />
                </label>
                <label class="table__field">
                  <span class="data-label">X</span>
                  <input
                    class="hud-input"
                    type="number"
                    step="0.5"
                    min="0"
                    data-testid="table-token-x"
                    bind:value={tokenDraft.x}
                  />
                </label>
                <label class="table__field">
                  <span class="data-label">Y</span>
                  <input
                    class="hud-input"
                    type="number"
                    step="0.5"
                    min="0"
                    data-testid="table-token-y"
                    bind:value={tokenDraft.y}
                  />
                </label>
                <label class="table__field">
                  <span class="data-label">Largura</span>
                  <input
                    class="hud-input"
                    type="number"
                    min="1"
                    data-testid="table-token-w"
                    bind:value={tokenDraft.w}
                  />
                </label>
                <label class="table__field">
                  <span class="data-label">Altura</span>
                  <input
                    class="hud-input"
                    type="number"
                    min="1"
                    data-testid="table-token-h"
                    bind:value={tokenDraft.h}
                  />
                </label>
                <label class="table__field">
                  <span class="data-label">Dono</span>
                  <input
                    class="hud-input"
                    type="text"
                    inputmode="numeric"
                    placeholder="Snowflake"
                    data-testid="table-token-owner"
                    bind:value={tokenDraft.owner}
                  />
                </label>
                <label class="table__field">
                  <span class="data-label">Personagem</span>
                  <input
                    class="hud-input"
                    type="text"
                    placeholder="chr_…"
                    data-testid="table-token-character"
                    bind:value={tokenDraft.character}
                  />
                </label>
                <label class="table__field">
                  <span class="data-label">Cor</span>
                  <input
                    class="hud-input"
                    type="text"
                    data-testid="table-token-color"
                    bind:value={tokenDraft.color}
                  />
                </label>
                <label class="table__check">
                  <input
                    type="checkbox"
                    data-testid="table-token-visible"
                    bind:checked={tokenDraft.visible}
                  />
                  <span>Visível para jogadores</span>
                </label>
              </div>
              <button
                class="hud-btn hud-btn--primary"
                type="button"
                data-testid="table-token-submit"
                disabled={busy !== ""}
                onclick={createToken}
              >
                Criar token
              </button>
            </section>
          {/if}

          {#if selected}
            <section class="table__panel" data-testid="table-token-selected">
              <h2 class="panel-label">Token</h2>
              <p class="data-value" data-testid="table-selected-label">
                {selected.label}
              </p>
              <p class="system-note">
                Célula {selected.x}, {selected.y} · {selected.w}×{selected.h}
              </p>
              <div class="table__keys">
                <button
                  class="hud-btn"
                  type="button"
                  data-testid="table-token-visibility"
                  disabled={busy !== ""}
                  onclick={() => toggleTokenVisibility(selected)}
                >
                  {selected.visible ? "Ocultar token" : "Mostrar token"}
                </button>
                <button
                  class="hud-btn hud-btn-danger"
                  type="button"
                  data-testid="table-token-remove"
                  disabled={busy !== ""}
                  onclick={() => removeToken(selected)}
                >
                  Remover token
                </button>
              </div>
            </section>
          {/if}
        {:else}
          <section class="table__panel">
            <h2 class="panel-label">Mesa</h2>
            <p class="system-note">
              {spectator
                ? "Você acompanha a mesa como espectador."
                : "O narrador conduz a mesa. Clique num token para abrir a ficha."}
            </p>
          </section>
        {/if}
      </aside>
    </div>
  {/if}

  {#if phase === "ready" && !table}
    {#if narrator}
      <form
        class="table__open"
        data-testid="table-open-form"
        onsubmit={(event) => {
          event.preventDefault();
          void openTable();
        }}
      >
        <h2 class="panel-label">Abrir mesa</h2>
        {#if failure}
          <p class="panel-error" role="alert" data-testid="table-open-error">
            <span class="stamp is-hazard">Hazard</span>
            <span>{failure}</span>
          </p>
        {/if}
        <div class="table__grid">
          <label class="table__field table__field--wide">
            <span class="data-label">Cena</span>
            <select
              class="hud-input"
              data-testid="table-open-scene"
              bind:value={openDraft.scene}
            >
              {#each cards as card (card.slug)}
                <option value={card.slug}>{card.name}</option>
              {/each}
            </select>
          </label>
          <label class="table__field table__field--wide">
            <span class="data-label">Canal de texto</span>
            <input
              class="hud-input"
              type="text"
              inputmode="numeric"
              placeholder="Snowflake do canal"
              data-testid="table-open-channel"
              bind:value={openDraft.channel}
            />
          </label>
          <label class="table__field table__field--wide">
            <span class="data-label">Nome da sessão</span>
            <input
              class="hud-input"
              type="text"
              placeholder="Sessão"
              data-testid="table-open-name"
              bind:value={openDraft.name}
            />
          </label>
        </div>
        <button
          class="hud-btn hud-btn--primary"
          type="submit"
          data-testid="table-open-submit"
          disabled={busy !== "" || cards.length === 0}
        >
          Abrir mesa
        </button>
        {#if cards.length === 0}
          <p class="system-note">
            Prepare uma cena em Cenas antes de abrir a mesa.
          </p>
        {/if}
      </form>
    {:else}
      <p class="system-note" data-testid="table-closed-note">
        A mesa não está aberta.
      </p>
    {/if}
  {/if}
</section>

{#if drawerOpen}
  <div
    class="drawer__backdrop"
    role="presentation"
    onclick={closeDrawer}
    data-testid="table-drawer-backdrop"
  ></div>
  <div
    class="drawer"
    role="dialog"
    aria-modal="true"
    aria-label="Ficha do token"
    data-testid="table-drawer"
  >
    <div class="drawer__bar">
      <h2 class="panel-label">Ficha</h2>
      <button
        class="hud-btn drawer__close"
        type="button"
        aria-label="Fechar ficha"
        data-testid="table-drawer-close"
        onclick={closeDrawer}
      >
        Fechar
      </button>
    </div>

    {#if drawerLoading}
      <p class="system-note">Carregando ficha…</p>
    {:else if drawerFailure}
      <p class="panel-error" role="alert" data-testid="table-drawer-error">
        <span class="stamp is-hazard">Hazard</span>
        <span>{drawerFailure}</span>
      </p>
    {:else if character}
      <div class="drawer__card">
        {#if character.card.portrait}
          <img class="drawer__portrait" src={character.card.portrait} alt="" />
        {/if}
        <div>
          <h3 class="drawer__name">{character.card.name}</h3>
          <p class="system-note">
            {character.card.concept ?? "Sem conceito"}
          </p>
        </div>
      </div>
      {#if character.kind === "sheet" && character.sheet}
        <SheetEditor
          {slug}
          sheet={character.sheet}
          onupdate={updateSheet}
          onreload={reloadSheet}
        />
      {:else}
        <p class="system-note" data-testid="table-drawer-card">
          Só o card público deste personagem está visível.
        </p>
      {/if}
    {:else if selected}
      <p class="data-value">{selected.label}</p>
      <p class="system-note">Este token não está ligado a um personagem.</p>
    {/if}
  </div>
{/if}

<style>
  .table {
    display: grid;
    gap: 1rem;
  }

  .table__retry {
    justify-self: start;
  }

  .table__banner {
    display: flex;
    flex-wrap: wrap;
    align-items: center;
    gap: 0.5rem;
    margin: 0;
  }

  .table__link {
    color: var(--amber);
    text-decoration: none;
    border-radius: var(--radius-key);
  }

  .table__link:focus-visible {
    outline: 2px solid var(--amber);
    outline-offset: 2px;
  }

  .table__notice {
    margin: 0;
  }

  .table__placards {
    display: flex;
    flex-wrap: wrap;
    gap: 0.5rem;
  }

  .table__placard {
    flex-direction: column;
    align-items: flex-start;
    gap: 0.3rem;
  }

  .table__body {
    display: grid;
    gap: 1rem;
    min-inline-size: 0;
  }

  .table__stage {
    min-inline-size: 0;
  }

  .table__column {
    display: grid;
    gap: 1rem;
    align-content: start;
    min-inline-size: 0;
  }

  .table__panel {
    display: grid;
    gap: 0.6rem;
    min-inline-size: 0;
    padding: 0.85rem;
    background: var(--plate-2);
    border-radius: var(--radius-plate);
  }

  .table__open {
    display: grid;
    gap: 0.75rem;
    max-inline-size: 34rem;
    padding: 0.85rem;
    background: var(--plate-2);
    border-radius: var(--radius-plate);
  }

  .table__grid {
    display: grid;
    grid-template-columns: repeat(2, minmax(0, 1fr));
    gap: 0.6rem;
  }

  .table__field {
    display: grid;
    gap: 0.3rem;
    min-inline-size: 0;
  }

  .table__field--wide {
    grid-column: 1 / -1;
  }

  .table__field .data-label {
    inline-size: auto;
  }

  .table__keys {
    display: flex;
    flex-wrap: wrap;
    gap: 0.5rem;
  }

  .table__check {
    display: flex;
    align-items: center;
    gap: 0.5rem;
    grid-column: 1 / -1;
    font-family: var(--font-label);
    font-size: 0.75rem;
    color: var(--label);
  }

  .drawer__backdrop {
    position: fixed;
    inset: 0;
    z-index: 30;
    background: rgb(0 0 0 / 0.6);
  }

  .drawer {
    position: fixed;
    inset-block: 0;
    inset-inline-end: 0;
    z-index: 40;
    inline-size: 28rem;
    max-inline-size: 100%;
    padding: 1rem;
    overflow-y: auto;
    background: var(--plate);
    border-inline-start: 1px solid var(--rule-strong);
  }

  .drawer__bar {
    display: flex;
    align-items: center;
    gap: 0.5rem;
    margin-block-end: 0.85rem;
  }

  .drawer__bar .panel-label {
    flex: 1;
    margin: 0;
  }

  .drawer__card {
    display: flex;
    align-items: center;
    gap: 0.75rem;
    margin-block-end: 0.85rem;
  }

  .drawer__portrait {
    inline-size: 4rem;
    block-size: 4rem;
    object-fit: cover;
    border: 1px solid var(--rule-strong);
    border-radius: var(--radius-key);
  }

  .drawer__name {
    margin: 0;
    font-family: var(--font-display);
    font-weight: 700;
    font-size: 1.1rem;
    color: var(--sand);
  }

  @media (max-width: 47.99rem) {
    .drawer {
      inline-size: 100%;
    }
  }

  @media (min-width: 56rem) {
    .table__body {
      grid-template-columns: minmax(0, 1fr) 20rem;
      align-items: start;
    }
  }
</style>
