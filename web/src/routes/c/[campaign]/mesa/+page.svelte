<script lang="ts">
  import { onMount, untrack } from "svelte";
  import { get } from "svelte/store";
  import { resolve } from "$app/paths";
  import { page } from "$app/state";
  import { ApiError, createApiClient } from "$lib/api";
  import { codeMessage } from "$lib/errors";
  import { isEditableTarget } from "$lib/keys";
  import { shellLinkLabel } from "$lib/shell";
  import SheetEditor from "$lib/components/SheetEditor.svelte";
  import TableMap from "$lib/components/TableMap.svelte";
  import { phaseForError } from "$lib/phase";
  import type { LoadPhase } from "$lib/phase";
  import { createTableLiveStore, startTableStream } from "$lib/table-stream";
  import type { TableStreamOptions } from "$lib/table-stream";
  import { createMovePump } from "$lib/table-moves";
  import {
    rollCursor,
    rollMessage,
    rollNote,
    rollSourceLabel,
  } from "$lib/rolls";
  import {
    canEndTurn,
    canPassTurn,
    nextPendingId,
    tableActionNote,
    tableOpenNote,
    tableRoleLabel,
    tableRoundLabel,
    tableSpectatorsLabel,
    tableStateNote,
    tableTokenNote,
    tableTurnNote,
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
  const ROLL_PAGE = 50;
  const slug = $derived(page.params.campaign ?? "");
  const queryTable = $derived(page.url.searchParams.get("table") ?? "");

  let phase = $state<LoadPhase>("loading");
  const live = createTableLiveStore();
  const table = $derived($live.summary);
  let campaignRole = $state<TableSummary["role"] | null>(null);
  let stream: { stop(): void } | null = null;
  let streamingId: string | null = null;
  let cards = $state<SceneSummary[]>([]);
  let busy = $state("");
  let failure = $state("");
  let notice = $state("");
  let warning = $state("");
  let moveLimited = $state(false);

  const moves = createMovePump({
    send: (batch) => {
      const current = table;
      if (!current) return Promise.resolve(null);
      return api.tableMoves(current.id, batch);
    },
    onLimited: (limited) => {
      moveLimited = limited;
    },
    onEnd: () => {
      live.setLocalDrag(null);
    },
  });

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

  let rollDraft = $state("");
  let rollSending = $state(false);

  const viewerRole = $derived(table?.role ?? campaignRole);
  const liveLink = $derived($live.link);
  const liveTableId = $derived(table?.id ?? null);
  const liveStatus = $derived(table?.status ?? null);
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
  const turn = $derived(table?.turn ?? null);
  const participants = $derived(table?.participants ?? []);
  const turnRole = $derived(viewerRole ?? "spectator");
  const passable = $derived(
    canPassTurn(turnRole, participants, turn, table?.viewer_id ?? null),
  );
  const endable = $derived(
    canEndTurn(turnRole, turn, table?.viewer_id ?? null),
  );
  const nextTurnId = $derived(nextPendingId(participants, turn));
  const waiting = $derived(
    turn !== null &&
      !participants.some((item) => item.token_id === turn.token_id),
  );
  const rollable = $derived(
    viewerRole === "narrator" || viewerRole === "player",
  );

  async function loadRolls(tableId: string) {
    try {
      let after = untrack(() => rollCursor(get(live).rolls));
      for (;;) {
        const batch = await api.tableRolls(tableId, after, ROLL_PAGE);
        if (batch.rolls.length === 0) return;
        live.addRolls(batch.rolls);
        if (batch.rolls.length < ROLL_PAGE) return;
        after = batch.rolls.at(-1)?.id ?? after;
      }
    } catch (error) {
      failure = rollNote(error);
    }
  }

  async function submitRoll() {
    const current = table;
    const expression = rollDraft.trim();
    if (current === null || expression === "" || rollSending) return;
    rollSending = true;
    failure = "";
    try {
      const result = await api.postTableRoll(current.id, { expression });
      live.addRolls(result.rolls);
      rollDraft = "";
    } catch (error) {
      failure = rollNote(error);
    } finally {
      rollSending = false;
    }
  }

  function syncStream() {
    const current = get(live).summary;
    const id = current?.status === "open" ? current.id : null;
    if (id === streamingId) return;
    stream?.stop();
    stream = null;
    streamingId = id;
    if (id === null) return;
    const options: TableStreamOptions = {
      tableId: id,
      store: live,
      onClosed: () => {
        stream = null;
        streamingId = null;
      },
      onError: (error) => {
        failure =
          codeMessage(error) ??
          (error instanceof Error && error.message
            ? error.message
            : "Não foi possível ler a mesa.");
      },
    };
    stream = startTableStream(options);
  }

  async function load(campaign: string, directTable: string) {
    phase = "loading";
    live.setSummary(null);
    cards = [];
    try {
      if (directTable) {
        const summary = await api.tableSummary(directTable);
        live.setSummary(summary);
        campaignRole = summary.role;
        sceneDraft = summary.scene?.slug ?? "";
        phase = "ready";
        syncStream();
        return;
      }
      const detail = await api.campaign(campaign);
      campaignRole = detail.role;
      cards =
        detail.role === "narrator" ? (await api.scenes(campaign)).scenes : [];
      const first = cards[0];
      if (first) openDraft.scene = first.slug;
      if (detail.open_table) {
        live.setSummary(await api.tableSummary(detail.open_table.id));
      }
      sceneDraft = get(live).summary?.scene?.slug ?? "";
      phase = "ready";
      syncStream();
    } catch (error) {
      phase = phaseForError(error);
    }
  }

  onMount(() => {
    void load(slug, queryTable);
    const onPageHide = () => {
      moves.flush();
    };
    window.addEventListener("pagehide", onPageHide);
    return () => {
      window.removeEventListener("pagehide", onPageHide);
      stream?.stop();
    };
  });

  let lastSheetRev = 0;

  $effect(() => {
    const changes = $live.sheetChanges;
    const latest = changes.at(-1);
    const sheet = character?.sheet;
    if (!latest || !sheet || sheet.id !== latest.sheet_id) return;
    if (latest.rev <= lastSheetRev) return;
    lastSheetRev = latest.rev;
    reloadSheet();
  });

  $effect(() => {
    if (liveTableId === null) return;
    if (liveStatus === "open" && liveLink !== "connected") return;
    void loadRolls(liveTableId);
  });

  $effect(() => {
    function onKey(event: KeyboardEvent) {
      if (isEditableTarget(event.target)) return;
      if (event.key === "Escape") {
        if (drawerOpen) closeDrawer();
        return;
      }
      if (event.key.toLowerCase() !== "n") return;
      if (event.metaKey || event.ctrlKey || event.altKey) return;
      if (!passable || nextTurnId === null) return;
      event.preventDefault();
      void changeTurn("pass", nextTurnId);
    }
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  });

  function adoptSummary(summary: TableSummary): TableSummary {
    live.setSummary(summary);
    syncStream();
    return summary;
  }

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
        const opened = adoptSummary(
          await api.openTable({
            campaign: slug,
            channel_id: openDraft.channel.trim(),
            scene: openDraft.scene,
            name: openDraft.name.trim() || null,
          }),
        );
        sceneDraft = opened.scene?.slug ?? "";
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
        adoptSummary(await api.closeTable(table!.id));
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
        const reopened = adoptSummary(await api.reopenTable(table!.id));
        warning = reopened.warning ?? "";
        sceneDraft = reopened.scene?.slug ?? "";
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
        adoptSummary(
          await api.changeTableScene(table!.id, {
            scene: sceneSlug,
          }),
        );
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
        const reloaded = adoptSummary(await api.reloadTableScene(table!.id));
        warning = reloaded.warning ?? "";
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
        adoptSummary(
          zone.revealed
            ? await api.hideZone(table!.id, zone.id)
            : await api.revealZone(table!.id, zone.id),
        );
        notice = zone.revealed ? "Área coberta." : "Área revelada.";
      } catch (error) {
        failure = tableZoneNote(error);
      }
    });
  }

  function beginTokenMove(token: TableToken, x: number, y: number) {
    if (!table || table.status !== "open") return;
    live.setLocalDrag(token.id);
    moves.begin(token.id, x, y);
  }

  function dragTokenTo(token: TableToken, x: number, y: number) {
    if (!table || table.status !== "open") return;
    live.moveLocal(token.id, x, y);
    moves.move(token.id, x, y);
  }

  function endTokenMove(token: TableToken, x: number, y: number) {
    if (!table || table.status !== "open") return;
    live.moveLocal(token.id, x, y);
    moves.end(token.id, x, y);
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
        adoptSummary(
          await api.createTableToken(table!.id, {
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
          }),
        );
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
        adoptSummary(
          await api.patchTableToken(table!.id, token.id, {
            visible: !token.visible,
          }),
        );
      } catch (error) {
        failure = tableTokenNote(error);
      }
    });
  }

  async function removeToken(token: TableToken) {
    if (!table || !narrator) return;
    await act("remove", async () => {
      try {
        adoptSummary(await api.deleteTableToken(table!.id, token.id));
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
        adoptSummary(
          await api.setTableSpectators(table!.id, {
            enabled: !table!.spectators,
          }),
        );
      } catch (error) {
        failure = tableActionNote(error);
      }
    });
  }

  async function changeTurn(action: "open" | "pass" | "end", tokenId?: string) {
    if (!table) return;
    await act(`turn-${action}`, async () => {
      try {
        adoptSummary(
          await api.tableTurn(table!.id, {
            action,
            token_id: tokenId ?? null,
            expected_turn_id: turn?.id ?? null,
          }),
        );
        notice =
          action === "open"
            ? "Turno aberto."
            : action === "pass"
              ? "Turno passado."
              : "Turno encerrado.";
      } catch (error) {
        failure = tableTurnNote(error);
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
        <span class="stamp is-hazard">Perigo</span>
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
    {#if moveLimited}
      <p class="placard table__notice" data-testid="table-move-limited">
        Rede limitada. O movimento vai mais devagar e volta sozinho.
      </p>
    {/if}
    {#if $live.closedReason}
      <p class="placard table__notice" data-testid="table-closed-event">
        {$live.closedReason}
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
            drags={$live.drags}
            ontoken={openToken}
            onzone={toggleZone}
            onmovestart={beginTokenMove}
            onmovemove={dragTokenTo}
            onmoveend={endTokenMove}
          />
        {:else}
          <p class="system-note">A mesa ainda não tem uma cena corrente.</p>
        {/if}
      </div>

      <aside class="table__column" aria-label="Mesa">
        <section class="table__panel" data-testid="table-viewers">
          <h2 class="panel-label">Na mesa</h2>
          <p class="system-note" data-testid="table-link">
            Vínculo: {shellLinkLabel($live.link)}
          </p>
          {#if $live.viewers.length === 0}
            <p class="system-note">Ninguém na mesa.</p>
          {:else}
            <ul class="turn__list">
              {#each $live.viewers as viewer, index (index)}
                <li class="turn__row" data-testid="table-viewer">
                  <span class="turn__label">{viewer.name}</span>
                  <span class="turn__state">
                    {tableRoleLabel(viewer.role)}
                  </span>
                </li>
              {/each}
            </ul>
          {/if}
        </section>

        {#if table.status === "open"}
          <section class="table__panel" data-testid="table-turn">
            <h2 class="panel-label">Turno</h2>
            <p class="system-note" data-testid="table-turn-state">
              {turn
                ? waiting
                  ? turn.label
                    ? `Aguardando ${turn.label}`
                    : "Aguardando"
                  : `Em turno: ${turn.label}`
                : "Sem turno aberto."}
            </p>
            {#if participants.length === 0}
              <p class="system-note" data-testid="table-turn-empty">
                Nenhum participante público nesta cena.
              </p>
            {:else}
              <ul class="turn__list">
                {#each participants as item (item.token_id)}
                  {@const current = turn?.token_id === item.token_id}
                  {@const pending = !item.acted}
                  <li
                    class="turn__row"
                    class:is-current={current}
                    class:is-acted={item.acted && !current}
                    data-testid={`table-participant-${item.token_id}`}
                  >
                    <span class="turn__label">{item.label}</span>
                    <span class="turn__state">
                      {current ? "Em turno" : item.acted ? "Agiu" : "Pendente"}
                    </span>
                    {#if pending && !current}
                      {#if narrator && !turn}
                        <button
                          class="hud-btn"
                          type="button"
                          aria-label={`Abrir turno de ${item.label}`}
                          data-testid={`table-turn-open-${item.token_id}`}
                          disabled={busy !== ""}
                          onclick={() => changeTurn("open", item.token_id)}
                        >
                          →
                        </button>
                      {:else if passable}
                        <button
                          class="hud-btn"
                          type="button"
                          aria-label={`Passar para ${item.label}`}
                          data-testid={`table-turn-pass-${item.token_id}`}
                          disabled={busy !== ""}
                          onclick={() => changeTurn("pass", item.token_id)}
                        >
                          →
                        </button>
                      {/if}
                    {/if}
                  </li>
                {/each}
              </ul>
            {/if}
            {#if endable}
              <div class="table__keys">
                <button
                  class="hud-btn"
                  type="button"
                  data-testid="table-turn-end"
                  disabled={busy !== ""}
                  onclick={() => changeTurn("end")}
                >
                  Encerrar turno
                </button>
              </div>
            {/if}
          </section>
        {/if}

        <section class="table__panel" data-testid="table-rolls">
          <h2 class="panel-label">Rolagem</h2>
          {#if rollable && table.status === "open"}
            <form
              class="table__roll"
              data-testid="table-roll-form"
              onsubmit={(event) => {
                event.preventDefault();
                void submitRoll();
              }}
            >
              <label class="table__field">
                <span class="data-label">Expressão</span>
                <input
                  class="hud-input"
                  type="text"
                  maxlength="120"
                  placeholder="4dF"
                  autocomplete="off"
                  spellcheck="false"
                  data-testid="table-roll-input"
                  disabled={rollSending}
                  bind:value={rollDraft}
                />
              </label>
              <button
                class="hud-btn hud-btn--primary"
                type="submit"
                data-testid="table-roll-submit"
                disabled={rollSending || rollDraft.trim() === ""}
              >
                Rolar
              </button>
            </form>
          {/if}
          {#if $live.rolls.length === 0}
            <p class="system-note" data-testid="table-roll-empty">
              Nenhuma rolagem ainda.
            </p>
          {:else}
            <ol class="roll__log" data-testid="table-roll-log">
              {#each $live.rolls as roll (roll.id)}
                <li class="roll__row" data-testid="table-roll">
                  <span
                    class="roll__tag"
                    class:is-discord={roll.source === "discord"}
                  >
                    {rollSourceLabel(roll.source)}
                  </span>
                  <span class="roll__text">{rollMessage(roll)}</span>
                </li>
              {/each}
            </ol>
          {/if}
        </section>

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
            <span class="stamp is-hazard">Perigo</span>
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
        <span class="stamp is-hazard">Perigo</span>
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

  .turn__list {
    display: grid;
    margin: 0;
    padding: 0;
    list-style: none;
  }

  .turn__row {
    display: flex;
    align-items: center;
    gap: 0.5rem;
    min-block-size: 2.5rem;
    padding-block: 0.35rem;
    border-block-start: 1px solid var(--rule);
  }

  .turn__row:first-child {
    border-block-start: 0;
  }

  .turn__label {
    flex: 1;
    min-inline-size: 0;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
    font-family: var(--font-value);
    color: var(--sand);
  }

  .turn__state {
    font-family: var(--font-label);
    font-size: 0.6875rem;
    line-height: 1;
    letter-spacing: 0.12em;
    text-transform: uppercase;
    color: var(--dim);
  }

  .turn__row.is-current .turn__state {
    color: var(--amber);
  }

  .turn__row.is-acted .turn__label {
    color: var(--dim);
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

  .table__roll {
    display: grid;
    grid-template-columns: minmax(0, 1fr) auto;
    align-items: end;
    gap: 0.5rem;
  }

  .roll__log {
    display: grid;
    gap: 0.35rem;
    max-block-size: 18rem;
    margin: 0;
    padding: 0;
    overflow-y: auto;
    list-style: none;
  }

  .roll__row {
    display: grid;
    grid-template-columns: auto minmax(0, 1fr);
    align-items: baseline;
    gap: 0.5rem;
    padding-block: 0.35rem;
    border-block-start: 1px solid var(--rule);
  }

  .roll__row:first-child {
    border-block-start: 0;
  }

  .roll__tag {
    font-family: var(--font-label);
    font-size: 0.6875rem;
    line-height: 1;
    letter-spacing: 0.12em;
    text-transform: uppercase;
    color: var(--amber);
  }

  .roll__tag.is-discord {
    color: var(--dim);
  }

  .roll__text {
    min-inline-size: 0;
    font-family: var(--font-value);
    font-size: 0.8125rem;
    line-height: 1.4;
    color: var(--sand);
    white-space: pre-wrap;
    overflow-wrap: anywhere;
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
