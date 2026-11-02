<script lang="ts">
  import { onMount, tick } from "svelte";
  import { resolve } from "$app/paths";
  import { page } from "$app/state";
  import { ApiError, createApiClient } from "$lib/api";
  import { isEditableTarget } from "$lib/keys";
  import { phaseForError } from "$lib/phase";
  import type { LoadPhase } from "$lib/phase";
  import {
    sceneEditorStateNote,
    sceneImageUrl,
    sceneSaveNote,
    sceneSavedLabel,
    sceneUsageSummary,
  } from "$lib/scenes";
  import {
    addRoom,
    canDraw,
    cellFromPoint,
    cellRect,
    clampCell,
    eraseCells,
    eraseLine,
    gridBounds,
    nextRoomLabel,
    outlinePath,
    zonesFit,
  } from "$lib/scene-draw";
  import type { Cell } from "$lib/scene-draw";
  import type {
    CampaignDetail,
    SceneDetail,
    SceneGrid,
    SceneSummary,
    SceneZone,
  } from "$lib/contract/panel.gen";

  type Tool = "select" | "room" | "erase";

  interface Drag {
    tool: "room" | "erase";
    start: Cell;
    end: Cell;
    touched: Cell[];
  }

  interface Snapshot {
    zones: SceneZone[];
    grid: SceneGrid;
    fogOutside: boolean;
    sceneName: string;
  }

  const TOOLS: Array<{ id: Tool; label: string; key: string }> = [
    { id: "select", label: "Selecionar", key: "V" },
    { id: "room", label: "Sala", key: "R" },
    { id: "erase", label: "Apagar", key: "E" },
  ];

  const api = createApiClient();

  let phase = $state<LoadPhase>("loading");
  let role = $state<CampaignDetail["role"] | null>(null);
  let detail = $state<SceneDetail | null>(null);
  let zones = $state<SceneZone[]>([]);
  let grid = $state<SceneGrid>({
    cell_px: 70,
    offset_x: 0,
    offset_y: 0,
    visible: true,
  });
  let fogOutside = $state(false);
  let openTable = $state(false);
  let sceneName = $state("");
  let sceneCards = $state<SceneSummary[]>([]);
  let labelEditing = $state(false);
  let selectedId = $state<string | null>(null);
  let tool = $state<Tool>("select");
  let drag = $state<Drag | null>(null);
  let history = $state<Snapshot[]>([]);
  let saving = $state(false);
  let dirty = $state(false);
  let failure = $state("");
  let notice = $state("");
  let stage = $state<SVGSVGElement | null>(null);
  let labelInput = $state<HTMLInputElement | null>(null);

  const slug = $derived(page.params.campaign ?? "");
  const sceneSlug = $derived(page.params.scene ?? "");
  const selected = $derived(
    zones.find((zone) => zone.id === selectedId) ?? null,
  );
  const bounds = $derived(
    gridBounds(detail?.image.width ?? 0, detail?.image.height ?? 0, grid),
  );
  const usage = $derived(
    sceneUsageSummary(
      openTable,
      0,
      zones.filter((zone) => zone.revealed).length,
      zones.length,
    ),
  );
  const editorState = $derived(
    dirty
      ? "Alterações não salvas"
      : detail
        ? sceneSavedLabel(detail.saved)
        : "",
  );

  function cloneZones(value: SceneZone[]): SceneZone[] {
    return value.map((zone) => ({
      ...zone,
      rects: zone.rects.map((rect) => ({ ...rect })),
    }));
  }

  function pushHistory() {
    history = [
      ...history,
      {
        zones: cloneZones(zones),
        grid: { ...grid },
        fogOutside,
        sceneName,
      },
    ];
  }

  function undo() {
    const previous = history[history.length - 1];
    if (!previous) return;
    zones = previous.zones;
    grid = { ...previous.grid };
    fogOutside = previous.fogOutside;
    sceneName = previous.sceneName;
    history = history.slice(0, -1);
    dirty = true;
    failure = "";
    notice = "";
    if (!zones.some((zone) => zone.id === selectedId)) selectedId = null;
  }

  function commit(next: SceneZone[], focusRoom = true) {
    if (JSON.stringify(next) === JSON.stringify(zones)) return;
    pushHistory();
    zones = next;
    dirty = true;
    failure = "";
    notice = "";
    if (focusRoom) {
      const target = next.find((zone) => zone.id === selectedId);
      if (!target) selectedId = next[next.length - 1]?.id ?? null;
    }
  }

  function selectRoom(zone: SceneZone | null) {
    selectedId = zone?.id ?? null;
  }

  function roomAt(cell: Cell): SceneZone | null {
    return (
      zones.find((zone) =>
        zone.rects.some(
          (rect) =>
            cell.x >= rect.x &&
            cell.y >= rect.y &&
            cell.x < rect.x + rect.w &&
            cell.y < rect.y + rect.h,
        ),
      ) ?? null
    );
  }

  function stagePoint(event: PointerEvent): Cell | null {
    if (!stage) return null;
    const matrix = stage.getScreenCTM();
    if (!matrix) return null;
    const point = stage.createSVGPoint();
    point.x = event.clientX;
    point.y = event.clientY;
    const local = point.matrixTransform(matrix.inverse());
    return { x: local.x, y: local.y };
  }

  function cellAt(event: PointerEvent): Cell | null {
    const point = stagePoint(event);
    if (!point) return null;
    return clampCell(cellFromPoint(point.x, point.y, grid), bounds);
  }

  function startDrag(event: PointerEvent, cell: Cell, kind: "room" | "erase") {
    drag = {
      tool: kind,
      start: cell,
      end: cell,
      touched: kind === "erase" ? [cell] : [],
    };
    (event.currentTarget as SVGSVGElement).setPointerCapture(event.pointerId);
  }

  function pointerDown(event: PointerEvent) {
    if (phase !== "ready" || role !== "narrator") return;
    if (event.pointerType === "mouse" && event.button !== 0) return;
    if (!canDraw(bounds)) return;
    const cell = cellAt(event);
    if (!cell) return;
    event.preventDefault();
    if (tool === "select") {
      selectRoom(roomAt(cell));
      return;
    }
    startDrag(event, cell, tool);
  }

  function pointerMove(event: PointerEvent) {
    if (!drag) return;
    const cell = cellAt(event);
    if (!cell) return;
    if (drag.tool === "erase") {
      const touched = [...drag.touched];
      for (const item of eraseLine(drag.end, cell)) {
        if (
          !touched.some(
            (cellItem) => cellItem.x === item.x && cellItem.y === item.y,
          )
        ) {
          touched.push(item);
        }
      }
      drag = { ...drag, end: cell, touched };
      return;
    }
    drag = { ...drag, end: cell };
  }

  function pointerUp(event: PointerEvent) {
    if (!drag) return;
    const current = drag;
    drag = null;
    (event.currentTarget as SVGSVGElement).releasePointerCapture(
      event.pointerId,
    );
    if (current.tool === "room") {
      const label = nextRoomLabel(zones);
      const before = new Map(
        zones.map((zone) => [zone.id, JSON.stringify(zone.rects)]),
      );
      const next = addRoom(zones, cellRect(current.start, current.end), label);
      const created = next.find(
        (zone) => !zones.some((existing) => existing.id === zone.id),
      );
      const changed =
        created ??
        next.find((zone) => before.get(zone.id) !== JSON.stringify(zone.rects));
      commit(next);
      if (changed) selectedId = changed.id;
      return;
    }
    commit(eraseCells(zones, current.touched));
  }

  function pointerCancel() {
    drag = null;
  }

  async function doubleClick(event: MouseEvent) {
    if (tool !== "select" || !stage) return;
    const point = stagePoint(event as unknown as PointerEvent);
    if (!point) return;
    const cell = clampCell(cellFromPoint(point.x, point.y, grid), bounds);
    const zone = roomAt(cell);
    if (!zone) return;
    selectRoom(zone);
    await tick();
    labelInput?.focus();
    labelInput?.select();
  }

  function deleteSelected() {
    if (!selected) return;
    commit(
      zones.filter((zone) => zone.id !== selected.id),
      false,
    );
    selectedId = null;
  }

  function keyDown(event: KeyboardEvent) {
    if (phase !== "ready" || role !== "narrator") return;
    if (isEditableTarget(event.target)) return;
    if ((event.ctrlKey || event.metaKey) && event.key.toLowerCase() === "z") {
      event.preventDefault();
      undo();
      return;
    }
    if (event.ctrlKey || event.metaKey || event.altKey) return;
    const key = event.key.toLowerCase();
    if (key === "v") {
      tool = "select";
      return;
    }
    if (key === "r") {
      tool = "room";
      return;
    }
    if (key === "e") {
      tool = "erase";
      return;
    }
    if (key === "s") {
      event.preventDefault();
      void save();
      return;
    }
    if (event.key === "Delete" || event.key === "Backspace") {
      event.preventDefault();
      deleteSelected();
    }
  }

  function updateGrid(patch: Partial<SceneGrid>) {
    pushHistory();
    grid = { ...grid, ...patch };
    dirty = true;
    failure = "";
    notice = "";
  }

  function updateZone(patch: Partial<SceneZone>) {
    if (!selected) return;
    pushHistory();
    zones = zones.map((zone) =>
      zone.id === selected.id ? { ...zone, ...patch } : zone,
    );
    dirty = true;
    failure = "";
    notice = "";
  }

  function numberValue(event: Event, fallback: number): number {
    const value = Number((event.currentTarget as HTMLInputElement).value);
    return Number.isFinite(value) ? value : fallback;
  }

  function gridCell(event: Event) {
    const value = Math.round(numberValue(event, grid.cell_px));
    updateGrid({ cell_px: Math.min(Math.max(value, 1), 1024) });
  }

  function gridOffset(axis: "offset_x" | "offset_y", event: Event) {
    const value = Math.round(numberValue(event, grid[axis]));
    updateGrid(axis === "offset_x" ? { offset_x: value } : { offset_y: value });
  }

  function toggleGrid(event: Event) {
    updateGrid({
      visible: (event.currentTarget as HTMLInputElement).checked,
    });
  }

  function toggleFog(event: Event) {
    pushHistory();
    fogOutside = (event.currentTarget as HTMLInputElement).checked;
    dirty = true;
    failure = "";
    notice = "";
  }

  function setLabel(event: Event) {
    if (labelEditing) {
      pushHistory();
      labelEditing = false;
    }
    zones = zones.map((zone) =>
      zone.id === selectedId
        ? { ...zone, label: (event.currentTarget as HTMLInputElement).value }
        : zone,
    );
    dirty = true;
  }

  function focusLabel() {
    labelEditing = true;
  }

  function renameScene(event: Event) {
    pushHistory();
    sceneName = (event.currentTarget as HTMLInputElement).value;
    dirty = true;
    failure = "";
    notice = "";
  }

  function toggleRevealed(event: Event) {
    updateZone({
      revealed: (event.currentTarget as HTMLInputElement).checked,
    });
  }

  async function save() {
    if (!detail || saving) return;
    if (!zonesFit(zones, bounds)) {
      failure = "Há salas fora do mapa. Ajuste a célula ou o offset.";
      return;
    }
    saving = true;
    failure = "";
    notice = "";
    try {
      const saved = await api.saveScene(slug, sceneSlug, {
        base_hash: detail.hash,
        name: sceneName,
        grid,
        fog_outside: fogOutside,
        zones,
      });
      detail = saved;
      zones = cloneZones(saved.zones);
      grid = { ...saved.grid };
      fogOutside = saved.fog_outside;
      sceneName = saved.name;
      sceneCards = sceneCards.map((card) =>
        card.slug === saved.slug
          ? {
              ...card,
              name: saved.name,
              zones: saved.zones,
              zone_count: saved.zones.length,
              grid: saved.grid,
              saved: true,
            }
          : card,
      );
      history = [];
      dirty = false;
      notice = "Cena salva.";
      if (!zones.some((zone) => zone.id === selectedId)) selectedId = null;
    } catch (error) {
      failure = sceneSaveNote(error);
      if (!(error instanceof ApiError)) throw error;
    } finally {
      saving = false;
    }
  }

  async function load() {
    phase = "loading";
    failure = "";
    notice = "";
    try {
      const campaign = await api.campaign(slug);
      role = campaign.role;
      openTable = campaign.open_table !== null;
      if (campaign.role !== "narrator") {
        phase = "ready";
        return;
      }
      const [loaded, listing] = await Promise.all([
        api.scene(slug, sceneSlug),
        api.scenes(slug),
      ]);
      detail = loaded;
      zones = cloneZones(loaded.zones);
      grid = { ...loaded.grid };
      fogOutside = loaded.fog_outside;
      sceneName = loaded.name;
      sceneCards = listing.scenes;
      selectedId = zones[0]?.id ?? null;
      history = [];
      dirty = false;
      phase = "ready";
    } catch (error) {
      role = null;
      detail = null;
      zones = [];
      phase = phaseForError(error);
    }
  }

  function roomAnchor(zone: SceneZone): { x: number; y: number } {
    const left = Math.min(...zone.rects.map((rect) => rect.x));
    const top = Math.min(...zone.rects.map((rect) => rect.y));
    const right = Math.max(...zone.rects.map((rect) => rect.x + rect.w));
    const bottom = Math.max(...zone.rects.map((rect) => rect.y + rect.h));
    return {
      x: ((left + right) / 2) * grid.cell_px + grid.offset_x,
      y: ((top + bottom) / 2) * grid.cell_px + grid.offset_y,
    };
  }

  function percent(value: number, total: number): string {
    return `${total > 0 ? (value / total) * 100 : 0}%`;
  }

  onMount(() => {
    void load();
  });
</script>

<svelte:head>
  <title>{sceneName || "Cena"} — Harpi</title>
</svelte:head>

<svelte:window onkeydown={keyDown} />

<section
  class="hud-panel editor"
  data-testid="scene-editor"
  aria-label="Editor de cena"
>
  <div class="panel-band editor__band">
    <a
      class="editor__back"
      href={resolve("/c/[campaign]/cenas", { campaign: slug })}
      data-testid="scene-back"
    >
      ← Galeria
    </a>
    <h1 class="panel-label">{sceneName || "Cena"}</h1>
    {#if detail}
      <span class="panel-band__meta">{detail.slug}</span>
    {/if}
  </div>

  {#if phase !== "ready"}
    <p class="system-note" data-testid="scene-editor-state">
      {sceneEditorStateNote(phase)}
    </p>
    {#if phase === "unavailable" || phase === "failed"}
      <button
        class="hud-btn editor__retry"
        type="button"
        data-testid="scene-editor-retry"
        onclick={() => load()}
      >
        Tentar de novo
      </button>
    {/if}
  {:else if role !== "narrator"}
    <p class="system-note" data-testid="scene-editor-forbidden">
      Só o narrador prepara as cenas.
    </p>
  {:else if detail}
    <p class="editor__usage" data-testid="scene-usage">
      <span>{usage}</span>
      <a
        class="editor__mesa"
        href={resolve("/c/[campaign]/mesa", { campaign: slug })}
        data-testid="scene-mesa-link"
      >
        Abrir Mesa
      </a>
    </p>

    {#if failure}
      <p class="panel-error" role="alert" data-testid="scene-editor-error">
        <span class="stamp is-hazard">Perigo</span>
        <span>{failure}</span>
        <button
          class="hud-btn"
          type="button"
          data-testid="scene-reload"
          onclick={() => load()}
        >
          Recarregar
        </button>
      </p>
    {:else if notice}
      <p class="placard editor__notice" data-testid="scene-editor-notice">
        {notice}
      </p>
    {/if}

    <div class="editor__bench">
      <div
        class="editor__tools"
        role="toolbar"
        aria-label="Ferramentas de desenho"
        data-testid="scene-tools"
      >
        {#each TOOLS as item (item.id)}
          <button
            class="hud-btn editor__tool"
            type="button"
            aria-pressed={tool === item.id}
            data-testid={`scene-tool-${item.id}`}
            onclick={() => (tool = item.id)}
          >
            <span>{item.label}</span>
            <kbd class="editor__key">{item.key}</kbd>
          </button>
        {/each}
        <button
          class="hud-btn editor__tool"
          type="button"
          data-testid="scene-undo"
          disabled={history.length === 0}
          onclick={undo}
        >
          <span>Desfazer</span>
          <kbd class="editor__key">Ctrl Z</kbd>
        </button>
      </div>

      <div class="editor__stage-wrap">
        <div
          class="editor__stage"
          style={`--scene-aspect: ${detail.image.width} / ${detail.image.height}`}
        >
          <svg
            bind:this={stage}
            class="editor__svg"
            data-source={detail.source}
            viewBox={`0 0 ${detail.image.width} ${detail.image.height}`}
            role="application"
            aria-label="Palco da cena"
            data-testid="scene-stage"
            onpointerdown={pointerDown}
            onpointermove={pointerMove}
            onpointerup={pointerUp}
            onpointercancel={pointerCancel}
            ondblclick={doubleClick}
          >
            <defs>
              <pattern
                id="scene-grid"
                width={grid.cell_px}
                height={grid.cell_px}
                x={grid.offset_x}
                y={grid.offset_y}
                patternUnits="userSpaceOnUse"
              >
                <path
                  d={`M ${grid.cell_px} 0 L 0 0 0 ${grid.cell_px}`}
                  fill="none"
                  stroke="var(--rule)"
                  stroke-width="1"
                />
              </pattern>
            </defs>
            <rect
              width={detail.image.width}
              height={detail.image.height}
              fill="var(--sunken)"
            />
            {#if detail.source === "image"}
              <image
                href={sceneImageUrl(slug, sceneSlug)}
                width={detail.image.width}
                height={detail.image.height}
                preserveAspectRatio="none"
              />
            {/if}
            {#each zones as zone (zone.id)}
              <path
                class="editor__room"
                class:is-selected={zone.id === selectedId}
                data-revealed={zone.revealed}
                d={outlinePath(zone, grid)}
              />
            {/each}
            {#if grid.visible}
              <rect
                class="editor__grid"
                width={detail.image.width}
                height={detail.image.height}
                fill="url(#scene-grid)"
                pointer-events="none"
              />
            {/if}
            {#if drag?.tool === "room"}
              {@const preview = cellRect(drag.start, drag.end)}
              <rect
                class="editor__preview"
                x={preview.x * grid.cell_px + grid.offset_x}
                y={preview.y * grid.cell_px + grid.offset_y}
                width={preview.w * grid.cell_px}
                height={preview.h * grid.cell_px}
                pointer-events="none"
              />
            {/if}
            {#if drag?.tool === "erase"}
              {#each drag.touched as cell (`${cell.x},${cell.y}`)}
                <rect
                  class="editor__erase"
                  x={cell.x * grid.cell_px + grid.offset_x}
                  y={cell.y * grid.cell_px + grid.offset_y}
                  width={grid.cell_px}
                  height={grid.cell_px}
                  pointer-events="none"
                />
              {/each}
            {/if}
          </svg>
          <div class="editor__labels" aria-hidden="true">
            {#each zones as zone (zone.id)}
              {@const anchor = roomAnchor(zone)}
              <span
                class="editor__label"
                class:is-hidden={!zone.revealed}
                style={`left: ${percent(anchor.x, detail.image.width)}; top: ${percent(anchor.y, detail.image.height)}`}
              >
                {zone.label}
                {#if !zone.revealed}
                  <span class="editor__hidden">oculta</span>
                {/if}
              </span>
            {/each}
          </div>
        </div>
        <p class="editor__hint" data-testid="scene-hint">
          Arraste com a ferramenta Sala para desenhar. A ferramenta Apagar corta
          só as células tocadas.
        </p>
      </div>

      <aside
        class="editor__inspector"
        data-testid="scene-inspector"
        aria-label="Inspetor"
      >
        <h2 class="panel-label">Inspetor</h2>

        <div class="editor__field">
          <span class="data-label">Cena</span>
          <label class="editor__row">
            <span>Nome</span>
            <input
              class="hud-input"
              type="text"
              maxlength="120"
              value={sceneName}
              data-testid="scene-name-input"
              onchange={renameScene}
            />
          </label>
          {#if sceneCards.length > 1}
            <ul class="editor__rooms" data-testid="scene-switch">
              {#each sceneCards as card (card.slug)}
                <li>
                  <a
                    class="editor__room-key"
                    class:is-selected={card.slug === sceneSlug}
                    href={resolve("/c/[campaign]/cenas/[scene]", {
                      campaign: slug,
                      scene: card.slug,
                    })}
                  >
                    <span>{card.name}</span>
                    <span class="editor__room-state"
                      >{card.zone_count} áreas</span
                    >
                  </a>
                </li>
              {/each}
            </ul>
          {/if}
        </div>

        <div class="editor__field">
          <span class="data-label">Grid</span>
          <label class="editor__row">
            <span>Célula (px)</span>
            <input
              class="hud-input"
              type="number"
              min="1"
              max="1024"
              value={grid.cell_px}
              data-testid="scene-cell"
              onchange={gridCell}
            />
          </label>
          <label class="editor__row">
            <span>Offset X</span>
            <input
              class="hud-input"
              type="number"
              value={grid.offset_x}
              data-testid="scene-offset-x"
              onchange={(event) => gridOffset("offset_x", event)}
            />
          </label>
          <label class="editor__row">
            <span>Offset Y</span>
            <input
              class="hud-input"
              type="number"
              value={grid.offset_y}
              data-testid="scene-offset-y"
              onchange={(event) => gridOffset("offset_y", event)}
            />
          </label>
          <label class="editor__check">
            <input
              type="checkbox"
              checked={grid.visible}
              data-testid="scene-grid-visible"
              onchange={toggleGrid}
            />
            <span>Grid visível</span>
          </label>
        </div>

        <div class="editor__field">
          <span class="data-label">Névoa</span>
          <label class="editor__check">
            <input
              type="checkbox"
              checked={fogOutside}
              data-testid="scene-fog-outside"
              onchange={toggleFog}
            />
            <span>Névoa fora das salas</span>
          </label>
        </div>

        <div class="editor__field">
          <span class="data-label">Salas</span>
          {#if zones.length === 0}
            <p class="system-note">Nenhuma sala ainda.</p>
          {:else}
            <ul class="editor__rooms" data-testid="scene-rooms">
              {#each zones as zone (zone.id)}
                <li>
                  <button
                    class="editor__room-key"
                    class:is-selected={zone.id === selectedId}
                    type="button"
                    data-testid="scene-room-key"
                    onclick={() => selectRoom(zone)}
                  >
                    <span>{zone.label}</span>
                    <span class="editor__room-state">
                      {zone.revealed ? "revelada" : "oculta"}
                    </span>
                  </button>
                </li>
              {/each}
            </ul>
          {/if}
        </div>

        {#if selected}
          <div class="editor__field" data-testid="scene-selected">
            <span class="data-label">Sala selecionada</span>
            <label class="editor__row">
              <span>Rótulo</span>
              <input
                bind:this={labelInput}
                class="hud-input"
                type="text"
                maxlength="80"
                value={selected.label}
                data-testid="scene-label"
                onfocus={focusLabel}
                oninput={setLabel}
              />
            </label>
            <label class="editor__check">
              <input
                type="checkbox"
                checked={selected.revealed}
                data-testid="scene-revealed"
                onchange={toggleRevealed}
              />
              <span>Revelada no início</span>
            </label>
            <button
              class="hud-btn hud-btn-danger"
              type="button"
              data-testid="scene-delete"
              onclick={deleteSelected}
            >
              Excluir sala
            </button>
          </div>
        {:else}
          <p class="system-note" data-testid="scene-no-selection">
            Clique numa sala para editar o rótulo.
          </p>
        {/if}

        <div class="editor__save">
          <span class="editor__state" data-testid="scene-editor-state-note">
            {editorState}
          </span>
          <button
            class="hud-btn hud-btn--primary"
            type="button"
            data-testid="scene-save"
            disabled={saving}
            onclick={() => save()}
          >
            {saving ? "Salvando…" : "Salvar"}
          </button>
        </div>
      </aside>
    </div>

    <div class="editor__strip" data-testid="scene-strip">
      {#if selected}
        <span class="data-label">Sala</span>
        <strong class="editor__strip-name">{selected.label}</strong>
        <span class="editor__strip-state" data-revealed={selected.revealed}>
          {selected.revealed ? "revelada" : "oculta"}
        </span>
        <span class="editor__strip-meta">
          {selected.rects.reduce((total, rect) => total + rect.w * rect.h, 0)}
          células
        </span>
      {:else}
        <span class="system-note">Nenhuma sala selecionada.</span>
      {/if}
    </div>
  {/if}
</section>

<style>
  .editor__band {
    flex-wrap: wrap;
    gap: 0.5rem;
  }

  .editor__back {
    color: var(--label);
    font-family: var(--font-label);
    font-weight: 600;
    font-size: 0.6875rem;
    letter-spacing: 0.12em;
    text-transform: uppercase;
    text-decoration: none;
    border-radius: var(--radius-key);
  }

  .editor__back:hover {
    color: var(--sand);
  }

  .editor__back:focus-visible {
    outline: 2px solid var(--amber);
    outline-offset: 2px;
  }

  .editor__retry {
    margin-block-start: 0.75rem;
  }

  .editor__usage {
    display: flex;
    flex-wrap: wrap;
    align-items: center;
    justify-content: space-between;
    gap: 0.5rem;
    margin: 0.85rem 0 0;
    padding: 0.5rem 0.7rem;
    border: 1px solid var(--rule-strong);
    border-radius: var(--radius-key);
    background: var(--rating);
    color: var(--dim);
    font-family: var(--font-value);
    font-size: 0.75rem;
  }

  .editor__mesa {
    color: var(--amber);
    font-family: var(--font-label);
    font-weight: 600;
    font-size: 0.6875rem;
    letter-spacing: 0.14em;
    text-transform: uppercase;
    text-decoration: none;
    border-radius: var(--radius-key);
  }

  .editor__mesa:focus-visible {
    outline: 2px solid var(--amber);
    outline-offset: 2px;
  }

  .editor__notice {
    margin-block-start: 0.85rem;
    color: var(--amber);
    font-family: var(--font-label);
    font-size: 0.6875rem;
    letter-spacing: 0.12em;
    text-transform: uppercase;
  }

  .editor__bench {
    display: grid;
    gap: 0.75rem;
    margin-block-start: 1rem;
  }

  .editor__tools {
    display: flex;
    flex-wrap: wrap;
    gap: 0.35rem;
  }

  .editor__tool {
    display: inline-flex;
    align-items: center;
    justify-content: space-between;
    gap: 0.5rem;
    min-inline-size: 6.5rem;
  }

  .editor__tool[aria-pressed="true"] {
    background: var(--plate-2);
    border-color: var(--sand);
    color: var(--sand);
  }

  .editor__key {
    font-family: var(--font-value);
    font-size: 0.6875rem;
    color: var(--faint);
  }

  .editor__stage-wrap {
    min-inline-size: 0;
  }

  .editor__stage {
    position: relative;
    border: 1px solid var(--rule-strong);
    border-radius: var(--radius-plate);
    background: var(--sunken);
    overflow: hidden;
  }

  .editor__svg {
    display: block;
    inline-size: 100%;
    block-size: auto;
    aspect-ratio: var(--scene-aspect);
    touch-action: none;
    cursor: crosshair;
  }

  .editor__svg:focus-visible {
    outline: 2px solid var(--amber);
    outline-offset: 2px;
  }

  .editor__room {
    fill: var(--plate-2);
    stroke: var(--rule-strong);
    stroke-width: 2;
    vector-effect: non-scaling-stroke;
    fill-rule: evenodd;
  }

  .editor__svg[data-source="image"] .editor__room {
    fill: color-mix(in srgb, var(--plate-2) 46%, transparent);
  }

  .editor__room[data-revealed="false"] {
    stroke: var(--faint);
    stroke-dasharray: 6 4;
  }

  .editor__room.is-selected {
    fill: color-mix(in srgb, var(--amber) 16%, var(--plate-2));
    stroke: var(--amber);
    stroke-width: 2;
  }

  .editor__preview {
    fill: color-mix(in srgb, var(--amber) 18%, transparent);
    stroke: var(--amber);
    stroke-width: 2;
    vector-effect: non-scaling-stroke;
  }

  .editor__erase {
    fill: color-mix(in srgb, var(--oxide) 26%, transparent);
  }

  .editor__grid {
    opacity: 0.6;
  }

  .editor__labels {
    position: absolute;
    inset: 0;
    pointer-events: none;
  }

  .editor__label {
    position: absolute;
    transform: translate(-50%, -50%);
    display: inline-flex;
    flex-wrap: wrap;
    align-items: center;
    justify-content: center;
    gap: 0.25rem;
    max-inline-size: 10rem;
    padding: 0.15rem 0.35rem;
    background: color-mix(in srgb, var(--ground) 82%, transparent);
    border: 1px solid var(--rule-strong);
    border-radius: var(--radius-key);
    color: var(--sand);
    font-family: var(--font-label);
    font-weight: 600;
    font-size: 0.6875rem;
    line-height: 1.1;
    letter-spacing: 0.1em;
    text-transform: uppercase;
    text-align: center;
  }

  .editor__label.is-hidden {
    border-style: dashed;
    color: var(--dim);
  }

  .editor__hidden {
    color: var(--faint);
    font-size: 0.6875rem;
  }

  .editor__hint {
    margin: 0.5rem 0 0;
    color: var(--faint);
    font-family: var(--font-value);
    font-size: 0.75rem;
  }

  .editor__inspector {
    display: grid;
    gap: 0.85rem;
    align-content: start;
    min-inline-size: 0;
  }

  .editor__field {
    display: grid;
    gap: 0.5rem;
    padding-block-end: 0.85rem;
    border-block-end: 1px solid var(--rule);
  }

  .editor__row {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 0.5rem;
    color: var(--label);
    font-family: var(--font-label);
    font-size: 0.6875rem;
    letter-spacing: 0.1em;
    text-transform: uppercase;
  }

  .editor__row .hud-input {
    inline-size: 6rem;
    text-align: end;
  }

  .editor__check {
    display: flex;
    align-items: center;
    gap: 0.5rem;
    color: var(--label);
    font-family: var(--font-label);
    font-size: 0.6875rem;
    letter-spacing: 0.1em;
    text-transform: uppercase;
    cursor: pointer;
  }

  .editor__check input {
    inline-size: 1rem;
    block-size: 1rem;
    accent-color: var(--amber);
  }

  .editor__rooms {
    display: grid;
    gap: 0.25rem;
    margin: 0;
    padding: 0;
    list-style: none;
  }

  .editor__room-key {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 0.5rem;
    inline-size: 100%;
    min-block-size: 2.5rem;
    padding: 0.35rem 0.5rem;
    border: 1px solid var(--rule);
    border-radius: var(--radius-key);
    background: transparent;
    color: var(--label);
    font-family: var(--font-label);
    font-size: 0.6875rem;
    letter-spacing: 0.1em;
    text-transform: uppercase;
    text-align: start;
    text-decoration: none;
    cursor: pointer;
  }

  .editor__room-key:hover,
  .editor__room-key.is-selected {
    background: var(--plate-2);
    border-color: var(--oxide);
    color: var(--sand);
  }

  .editor__room-key.is-selected {
    border-color: var(--amber);
  }

  .editor__room-key:focus-visible {
    outline: 2px solid var(--amber);
    outline-offset: 2px;
  }

  .editor__room-state {
    color: var(--faint);
    font-family: var(--font-value);
    font-size: 0.6875rem;
    letter-spacing: 0.02em;
    text-transform: none;
  }

  .editor__save {
    display: grid;
    gap: 0.5rem;
  }

  .editor__state {
    color: var(--dim);
    font-family: var(--font-label);
    font-size: 0.6875rem;
    letter-spacing: 0.12em;
    text-transform: uppercase;
  }

  .editor__strip {
    display: flex;
    flex-wrap: wrap;
    align-items: center;
    gap: 0.5rem;
    margin-block-start: 0.85rem;
    padding: 0.5rem 0.7rem;
    border: 1px solid var(--rule-strong);
    border-radius: var(--radius-key);
    background: var(--plate);
  }

  .editor__strip-name {
    color: var(--sand);
    font-family: var(--font-display);
    font-weight: 700;
    font-size: 0.95rem;
  }

  .editor__strip-state {
    color: var(--faint);
    font-family: var(--font-label);
    font-size: 0.6875rem;
    letter-spacing: 0.12em;
    text-transform: uppercase;
  }

  .editor__strip-state[data-revealed="true"] {
    color: var(--amber);
  }

  .editor__strip-meta {
    margin-inline-start: auto;
    color: var(--faint);
    font-family: var(--font-value);
    font-size: 0.75rem;
  }

  @media (min-width: 56rem) {
    .editor__bench {
      grid-template-columns: 7rem minmax(0, 1fr) 17rem;
      align-items: start;
    }

    .editor__tools {
      flex-direction: column;
      flex-wrap: nowrap;
    }

    .editor__tool {
      inline-size: 100%;
    }
  }
</style>
