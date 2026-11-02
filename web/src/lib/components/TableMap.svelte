<script lang="ts">
  import type {
    TableDragMarker,
    TableScene,
    TableSummary,
    TableToken,
    SceneZone,
  } from "$lib/contract/panel.gen";
  import {
    gridColumns,
    mapMinWidth,
    rectsPath,
    tokenBox,
    zoneLabelPoint,
    zonePath,
  } from "$lib/tables";

  type TableRole = TableSummary["role"];

  let {
    scene,
    tokens,
    role,
    viewerId = null,
    selectedId = null,
    drags = [],
    ontoken = () => {},
    onzone = () => {},
    onmovestart = () => {},
    onmovemove = () => {},
    onmoveend = () => {},
  }: {
    scene: TableScene;
    tokens: TableToken[];
    role: TableRole;
    viewerId?: string | null;
    selectedId?: string | null;
    drags?: TableDragMarker[];
    ontoken?: (token: TableToken) => void;
    onzone?: (zone: SceneZone) => void;
    onmovestart?: (token: TableToken, x: number, y: number) => void;
    onmovemove?: (token: TableToken, x: number, y: number) => void;
    onmoveend?: (token: TableToken, x: number, y: number) => void;
  } = $props();

  let zoom = $state(1);
  let surface = $state<HTMLElement | null>(null);
  let suppressClick = false;
  let localPos: Record<string, { x: number; y: number; writes: string[] }> = {};
  let drag = $state<{
    id: string;
    startX: number;
    startY: number;
    originX: number;
    originY: number;
    x: number;
    y: number;
    moved: boolean;
  } | null>(null);

  const narrator = $derived(role === "narrator");
  const columns = $derived(gridColumns(scene));
  const rows = $derived(
    Math.max(
      1,
      Math.ceil((scene.height - scene.grid.offset_y) / scene.grid.cell_px),
    ),
  );
  const fogVisible = $derived(!narrator && scene.fog_outside);
  const cellPx = $derived(scene.grid.cell_px);
  const markers = $derived(
    new Map(drags.map((marker) => [marker.token_id, marker])),
  );

  function movable(token: TableToken): boolean {
    if (narrator) return true;
    return (
      role === "player" &&
      token.owner_id !== null &&
      token.owner_id === viewerId
    );
  }

  function remoteDrag(token: TableToken): TableDragMarker | null {
    if (drag?.id === token.id) return null;
    return markers.get(token.id) ?? null;
  }

  function tokenStyle(token: TableToken): string {
    const box = tokenBox(
      drag?.id === token.id ? { ...token, x: drag.x, y: drag.y } : token,
      scene,
    );
    return `left:${box.left}%;top:${box.top}%;width:${box.width}%;height:${box.height}%`;
  }

  function tokenClass(token: TableToken): string {
    const names = ["map__token"];
    names.push(token.owner_id === null ? "is-npc" : "is-pc");
    if (token.owner_id !== null && token.owner_id === viewerId) {
      names.push("is-own");
    }
    if (!token.visible) names.push("is-hidden");
    if (token.id === selectedId) names.push("is-selected");
    return names.join(" ");
  }

  function tokenLabel(token: TableToken): string {
    return `${token.label}${token.visible ? "" : " (oculto)"}`;
  }

  function clamp(value: number, minimum: number, maximum: number): number {
    return Math.min(Math.max(value, minimum), maximum);
  }

  function snap(value: number): number {
    return Math.round(value * 2) / 2;
  }

  function startDrag(event: PointerEvent, token: TableToken) {
    if (!movable(token)) return;
    suppressClick = false;
    const element = event.currentTarget as HTMLElement;
    element.setPointerCapture(event.pointerId);
    drag = {
      id: token.id,
      startX: event.clientX,
      startY: event.clientY,
      originX: token.x,
      originY: token.y,
      x: token.x,
      y: token.y,
      moved: false,
    };
    event.preventDefault();
  }

  function moveDrag(event: PointerEvent) {
    if (!drag || !surface) return;
    const rect = surface.getBoundingClientRect();
    const cell = rect.width * (cellPx / scene.width) || 1;
    const dx = (event.clientX - drag.startX) / cell;
    const dy = (event.clientY - drag.startY) / cell;
    const token = tokens.find((item) => item.id === drag?.id);
    if (!token) return;
    const x = snap(clamp(drag.originX + dx, 0, columns - token.w));
    const y = snap(clamp(drag.originY + dy, 0, rows - token.h));
    const moved = x !== drag.x || y !== drag.y;
    if (moved && !drag.moved) onmovestart(token, x, y);
    drag = { ...drag, x, y, moved: drag.moved || moved };
    if (moved) onmovemove(token, x, y);
  }

  function endDrag(event: PointerEvent, token: TableToken) {
    const current = drag;
    if (!current) return;
    drag = null;
    suppressClick = current.moved;
    if (suppressClick) {
      setTimeout(() => (suppressClick = false), 250);
    }
    if (event.currentTarget instanceof HTMLElement) {
      event.currentTarget.releasePointerCapture(event.pointerId);
    }
    if (current.moved) onmoveend(token, snap(current.x), snap(current.y));
  }

  function cancelDrag(token: TableToken) {
    const current = drag;
    drag = null;
    if (current?.moved) {
      onmoveend(token, snap(current.x), snap(current.y));
    }
  }

  function pickToken(event: MouseEvent, token: TableToken) {
    if (suppressClick) return;
    event.stopPropagation();
    ontoken(token);
  }

  function baseOf(token: TableToken): {
    x: number;
    y: number;
    writes: string[];
  } {
    const local = localPos[token.id];
    if (!local) return { x: token.x, y: token.y, writes: [] };
    if (local.x === token.x && local.y === token.y) return local;
    if (local.writes.includes(`${token.x},${token.y}`)) return local;
    return { x: token.x, y: token.y, writes: [] };
  }

  function tokenKey(event: KeyboardEvent, token: TableToken) {
    if (event.key === "Enter") {
      event.preventDefault();
      ontoken(token);
      return;
    }
    if (!movable(token)) return;
    const step = event.shiftKey ? 5 : 1;
    const moves: Record<string, [number, number]> = {
      ArrowLeft: [-step, 0],
      ArrowRight: [step, 0],
      ArrowUp: [0, -step],
      ArrowDown: [0, step],
    };
    const move = moves[event.key];
    if (!move) return;
    event.preventDefault();
    const base = baseOf(token);
    const x = clamp(base.x + move[0], 0, columns - token.w);
    const y = clamp(base.y + move[1], 0, rows - token.h);
    localPos = {
      ...localPos,
      [token.id]: {
        x,
        y,
        writes: [...base.writes, `${base.x},${base.y}`].slice(-8),
      },
    };
    onmoveend(token, x, y);
  }

  function zoneKey(event: KeyboardEvent, zone: SceneZone) {
    if (!narrator) return;
    if (event.key !== "Enter" && event.key !== " ") return;
    event.preventDefault();
    onzone(zone);
  }

  function zoomBy(step: number) {
    zoom = clamp(Math.round((zoom + step) * 10) / 10, 1, 3);
  }
</script>

<div class="map" data-testid="table-map">
  <div class="map__bar">
    <span class="map__caption" data-testid="table-scene-name">
      {scene.name}
    </span>
    <div class="map__zoom" role="group" aria-label="Zoom do mapa">
      <button
        class="hud-btn map__key"
        type="button"
        aria-label="Diminuir zoom"
        data-testid="map-zoom-out"
        onclick={() => zoomBy(-0.25)}
      >
        −
      </button>
      <button
        class="hud-btn map__key"
        type="button"
        aria-label="Aumentar zoom"
        data-testid="map-zoom-in"
        onclick={() => zoomBy(0.25)}
      >
        ＋
      </button>
      <button
        class="hud-btn map__key map__fit"
        type="button"
        data-testid="map-fit"
        onclick={() => (zoom = 1)}
      >
        Enquadrar
      </button>
    </div>
  </div>

  <div class="map__viewport" data-testid="table-map-viewport">
    <div
      class="map__surface"
      bind:this={surface}
      style={`aspect-ratio:${scene.width} / ${scene.height};inline-size:${zoom * 100}%;--map-min:${mapMinWidth(scene)}`}
      data-testid="table-map-surface"
    >
      <img
        class="map__image"
        src={scene.map_url}
        alt={`Mapa de ${scene.name}`}
        draggable="false"
      />

      <svg
        class="map__overlay"
        viewBox={`0 0 ${scene.width} ${scene.height}`}
        preserveAspectRatio="none"
      >
        <defs>
          <pattern
            id="table-map-grid"
            width={cellPx}
            height={cellPx}
            patternUnits="userSpaceOnUse"
            x={scene.grid.offset_x}
            y={scene.grid.offset_y}
          >
            <path
              d={`M ${cellPx} 0 L 0 0 0 ${cellPx}`}
              fill="none"
              stroke="var(--rule)"
              stroke-width="1"
            />
          </pattern>
          <pattern
            id="table-map-hatch"
            width="14"
            height="14"
            patternUnits="userSpaceOnUse"
            patternTransform="rotate(45)"
          >
            <line
              x1="0"
              y1="0"
              x2="0"
              y2="14"
              stroke="var(--rule-strong)"
              stroke-width="1"
            />
          </pattern>
          <mask id="table-map-fog">
            <rect
              x="0"
              y="0"
              width={scene.width}
              height={scene.height}
              fill="white"
            />
            {#each scene.zones.filter((item) => item.revealed) as zone (zone.id)}
              <path d={zonePath(zone, scene.grid)} fill="black" />
            {/each}
          </mask>
        </defs>

        {#if scene.grid.visible}
          <rect
            x="0"
            y="0"
            width={scene.width}
            height={scene.height}
            fill="url(#table-map-grid)"
            class="map__grid"
          />
        {/if}

        {#each scene.zones as zone (zone.id)}
          <a
            class="map__zone"
            class:is-hidden={!zone.revealed}
            class:is-clickable={narrator}
            role={narrator ? "button" : undefined}
            tabindex={narrator ? 0 : undefined}
            href={narrator ? `#${zone.id}` : undefined}
            aria-label={narrator
              ? `${zone.label}: ${zone.revealed ? "revelada" : "oculta"}`
              : undefined}
            onclick={(event) => {
              if (!narrator) return;
              event.preventDefault();
              onzone(zone);
            }}
            onkeydown={(event) => zoneKey(event, zone)}
            data-testid={`map-zone-${zone.id}`}
          >
            <path class="map__zone-path" d={zonePath(zone, scene.grid)} />
            {#if narrator || zone.revealed}
              {@const point = zoneLabelPoint(zone, scene.grid)}
              <text
                class="map__zone-label"
                x={point.x}
                y={point.y}
                text-anchor="middle"
                dominant-baseline="middle"
              >
                {zone.label}
              </text>
            {/if}
          </a>
        {/each}

        {#if !narrator && !scene.fog_outside && scene.fog.length > 0}
          <path
            class="map__fog"
            d={rectsPath(scene.fog, scene.grid)}
            mask="url(#table-map-fog)"
          />
        {/if}

        {#if fogVisible}
          <rect
            class="map__fog"
            x="0"
            y="0"
            width={scene.width}
            height={scene.height}
            mask="url(#table-map-fog)"
          />
        {/if}
      </svg>

      {#each tokens as token (token.id)}
        {@const remote = remoteDrag(token)}
        <div
          class="map__token-slot"
          class:is-selected={token.id === selectedId}
          style={tokenStyle(token)}
        >
          <button
            class={tokenClass(token)}
            class:is-remote-drag={remote !== null}
            type="button"
            aria-label={tokenLabel(token)}
            aria-pressed={token.id === selectedId}
            data-testid={`table-token-${token.id}`}
            onpointerdown={(event) => startDrag(event, token)}
            onpointermove={moveDrag}
            onpointerup={(event) => endDrag(event, token)}
            onpointercancel={() => cancelDrag(token)}
            onclick={(event) => pickToken(event, token)}
            onkeydown={(event) => tokenKey(event, token)}
            style={`cursor:${movable(token) ? "grab" : "pointer"}`}
          >
            <span class="visually-hidden">{token.label}</span>
          </button>
          {#if remote}
            <span class="map__drag-tag" data-testid={`table-drag-${token.id}`}>
              {remote.actor}
            </span>
          {/if}
          <span class="map__token-label">{token.label}</span>
        </div>
      {/each}
    </div>
  </div>
</div>

<style>
  .map {
    min-inline-size: 0;
  }

  .map__bar {
    display: flex;
    align-items: center;
    gap: 0.5rem;
    margin-block-end: 0.5rem;
  }

  .map__caption {
    font-family: var(--font-display);
    font-weight: 700;
    font-size: 0.9rem;
    letter-spacing: 0.06em;
    color: var(--sand);
  }

  .map__zoom {
    display: flex;
    gap: 0.35rem;
    margin-inline-start: auto;
  }

  .map__key {
    min-inline-size: 2.5rem;
    padding-inline: 0.55rem;
  }

  .map__fit {
    min-inline-size: 5.5rem;
  }

  .map__viewport {
    overflow: auto;
    border: 1px solid var(--rule-strong);
    border-radius: var(--radius-plate);
    background: var(--sunken);
    max-block-size: 62vh;
  }

  .map__surface {
    position: relative;
    min-inline-size: 100%;
    margin-inline: auto;
  }

  .map__image {
    position: absolute;
    inset: 0;
    inline-size: 100%;
    block-size: 100%;
    object-fit: fill;
    user-select: none;
  }

  .map__overlay {
    position: absolute;
    inset: 0;
    inline-size: 100%;
    block-size: 100%;
    overflow: visible;
  }

  .map__grid {
    pointer-events: none;
  }

  .map__zone-path {
    fill: transparent;
    stroke: var(--rule-strong);
    stroke-width: 2;
    vector-effect: non-scaling-stroke;
  }

  .map__zone.is-hidden .map__zone-path {
    fill: url(#table-map-hatch);
    stroke-dasharray: 6 5;
  }

  .map__zone.is-clickable {
    cursor: pointer;
  }

  .map__zone.is-clickable:focus-visible .map__zone-path {
    outline: 2px solid var(--amber);
    outline-offset: 2px;
  }

  .map__zone-label {
    font-family: var(--font-label);
    font-weight: 600;
    font-size: 13px;
    letter-spacing: 0.14em;
    text-transform: uppercase;
    fill: var(--sand);
    stroke: var(--sunken);
    stroke-width: 3;
    paint-order: stroke;
    pointer-events: none;
  }

  .map__fog {
    fill: var(--sunken);
    opacity: 0.9;
    pointer-events: none;
  }

  .map__token-slot {
    position: absolute;
    display: flex;
    align-items: center;
    justify-content: center;
    pointer-events: none;
  }

  .map__token {
    position: relative;
    inline-size: 100%;
    block-size: 100%;
    min-inline-size: 2.25rem;
    min-block-size: 2.25rem;
    padding: 0;
    border: 3px solid;
    border-radius: var(--radius-key);
    background: color-mix(in srgb, var(--plate-2) 62%, transparent);
    pointer-events: auto;
    touch-action: none;
    transition:
      border-color var(--motion-quick) ease,
      box-shadow var(--motion-quick) ease;
  }

  .map__token.is-pc {
    border-color: var(--sand);
  }

  .map__token.is-npc {
    border-color: var(--oxide);
  }

  .map__token.is-own {
    box-shadow: 0 0 0 2px var(--amber);
  }

  .map__token.is-hidden {
    border-style: dashed;
    opacity: 0.6;
  }

  .map__token.is-selected {
    box-shadow: 0 0 0 2px var(--oxide);
  }

  .map__token.is-remote-drag {
    border-color: var(--oxide);
    border-style: dashed;
  }

  .map__drag-tag {
    position: absolute;
    inset-block-end: 100%;
    inset-inline-start: 50%;
    translate: -50% -0.25rem;
    padding: 0.15rem 0.4rem;
    background: var(--plate-2);
    border: 1px dashed var(--oxide);
    border-radius: var(--radius-key);
    font-family: var(--font-label);
    font-weight: 600;
    font-size: 0.6875rem;
    line-height: 1;
    letter-spacing: 0.12em;
    text-transform: uppercase;
    white-space: nowrap;
    color: var(--oxide);
    pointer-events: none;
  }

  .map__token.is-selected.is-own {
    box-shadow:
      0 0 0 2px var(--amber),
      0 0 0 4px var(--oxide);
  }

  .map__token:hover {
    border-color: var(--oxide);
  }

  .map__token:focus-visible {
    outline: 2px solid var(--amber);
    outline-offset: 2px;
  }

  .map__token-label {
    position: absolute;
    inset-block-start: 100%;
    inset-inline-start: 50%;
    translate: -50% 0.25rem;
    padding: 0.2rem 0.4rem;
    background: var(--plate-2);
    border-radius: var(--radius-key);
    font-family: var(--font-label);
    font-weight: 600;
    font-size: 0.6875rem;
    line-height: 1;
    letter-spacing: 0.12em;
    text-transform: uppercase;
    white-space: nowrap;
    color: var(--sand);
    pointer-events: none;
  }

  @media (max-width: 48rem) {
    .map__surface {
      inline-size: 100%;
      min-inline-size: var(--map-min);
    }

    .map__token-label {
      display: none;
    }

    .map__viewport {
      max-block-size: 55vh;
    }
  }
</style>
