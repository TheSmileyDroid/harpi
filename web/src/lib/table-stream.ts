import { writable } from "svelte/store";
import type {
  TableDragMarker,
  TableSheetChanged,
  TableSummary,
  TablePresenceEntry,
} from "./contract/panel.gen";
import { createTableEventStream } from "./sse";
import type { AwakeTargets, EventSourceLike, TableSseFrame } from "./sse";

export type TableLink = "connecting" | "connected" | "reconnecting";

export interface TableLiveState {
  summary: TableSummary | null;
  streamRev: number;
  viewers: TablePresenceEntry[];
  drags: TableDragMarker[];
  sheetChanges: TableSheetChanged[];
  closedReason: string | null;
  link: TableLink;
}

export interface TableReduceOutcome {
  state: TableLiveState;
  diverged: boolean;
  closed: boolean;
}

export function initialTableLive(): TableLiveState {
  return {
    summary: null,
    streamRev: 0,
    viewers: [],
    drags: [],
    sheetChanges: [],
    closedReason: null,
    link: "connecting",
  };
}

function linkState(state: string): TableLink {
  if (state === "connected" || state === "reconnecting") return state;
  return "connecting";
}

function mergeTokens(
  summary: TableSummary,
  frame: Extract<TableSseFrame, { type: "table.delta" }>,
): TableSummary["tokens"] {
  const removed = new Set(frame.data.removed);
  const tokens = summary.tokens.filter((token) => !removed.has(token.id));
  for (const token of frame.data.tokens) {
    const index = tokens.findIndex((item) => item.id === token.id);
    if (index === -1) tokens.push(token);
    else tokens[index] = token;
  }
  return tokens;
}

function applyDelta(
  summary: TableSummary,
  frame: Extract<TableSseFrame, { type: "table.delta" }>,
): TableSummary {
  return {
    ...summary,
    scene: frame.data.scene ?? summary.scene,
    tokens: mergeTokens(summary, frame),
    turn: frame.data.turn,
    round: frame.data.round,
    status: frame.data.status,
    spectators: frame.data.spectators,
    participants: frame.data.participants,
  };
}

function deltaSceneMatches(
  summary: TableSummary,
  frame: Extract<TableSseFrame, { type: "table.delta" }>,
): boolean {
  return frame.data.scene_id === (summary.scene?.id ?? null);
}

function reduceDrag(
  drags: TableDragMarker[],
  frame: Extract<TableSseFrame, { type: "table.drag" }>,
): TableDragMarker[] {
  const rest = drags.filter((drag) => drag.token_id !== frame.data.token_id);
  return frame.data.active ? [...rest, { ...frame.data }] : rest;
}

function reduceSheet(
  changes: TableSheetChanged[],
  frame: Extract<TableSseFrame, { type: "sheet.changed" }>,
): TableSheetChanged[] {
  return [
    ...changes.filter((item) => item.sheet_id !== frame.data.sheet_id),
    frame.data,
  ];
}

export function reduceTableFrame(
  state: TableLiveState,
  frame: TableSseFrame,
): TableReduceOutcome {
  if (frame.type === "table.snapshot") {
    return {
      state: {
        ...state,
        summary: frame.data.state,
        streamRev: frame.data.stream_rev,
        viewers: frame.data.viewers,
        drags: frame.data.drags,
        closedReason: null,
      },
      diverged: false,
      closed: false,
    };
  }
  if (frame.type === "table.delta") {
    if (state.summary === null || !deltaSceneMatches(state.summary, frame)) {
      return { state, diverged: true, closed: false };
    }
    if (frame.data.from_stream_rev !== state.streamRev) {
      return { state, diverged: true, closed: false };
    }
    return {
      state: {
        ...state,
        summary: applyDelta(state.summary, frame),
        streamRev: frame.data.stream_rev,
      },
      diverged: false,
      closed: false,
    };
  }
  if (frame.type === "table.viewers") {
    return {
      state: { ...state, viewers: frame.data.viewers },
      diverged: false,
      closed: false,
    };
  }
  if (frame.type === "table.drag") {
    return {
      state: { ...state, drags: reduceDrag(state.drags, frame) },
      diverged: false,
      closed: false,
    };
  }
  if (frame.type === "sheet.changed") {
    return {
      state: {
        ...state,
        sheetChanges: reduceSheet(state.sheetChanges, frame),
      },
      diverged: false,
      closed: false,
    };
  }
  if (frame.type === "table.closed") {
    return {
      state: {
        ...state,
        summary:
          state.summary === null
            ? null
            : { ...state.summary, status: "closed" },
        closedReason: frame.data.reason,
      },
      diverged: false,
      closed: true,
    };
  }
  return { state, diverged: false, closed: false };
}

export function createTableLiveStore() {
  const { subscribe, update, set } =
    writable<TableLiveState>(initialTableLive());
  return {
    subscribe,
    setSummary(summary: TableSummary | null): void {
      update((state) => ({
        ...state,
        summary,
        closedReason: summary?.status === "open" ? null : state.closedReason,
      }));
    },
    setLink(link: string): void {
      update((state) => ({ ...state, link: linkState(link) }));
    },
    apply(frame: TableSseFrame): TableReduceOutcome {
      let outcome: TableReduceOutcome = {
        state: initialTableLive(),
        diverged: false,
        closed: false,
      };
      update((state) => {
        outcome = reduceTableFrame(state, frame);
        return outcome.state;
      });
      return outcome;
    },
    reset(): void {
      set(initialTableLive());
    },
  };
}

type TableLiveStore = ReturnType<typeof createTableLiveStore>;

export interface TableStreamOptions {
  tableId: string;
  store: TableLiveStore;
  EventSourceImpl?: new (
    url: string,
    options?: { withCredentials?: boolean },
  ) => EventSourceLike;
  schedule?: (fn: () => void, timeout: number) => ReturnType<typeof setTimeout>;
  cancel?: (id: ReturnType<typeof setTimeout>) => void;
  awake?: AwakeTargets | null;
  onError?: (error: unknown) => void;
  onClosed?: () => void;
}

export function startTableStream(options: TableStreamOptions) {
  const control: {
    current: ReturnType<typeof createTableEventStream> | null;
  } = { current: null };
  const stream = createTableEventStream({
    tableId: options.tableId,
    ...(options.EventSourceImpl
      ? { EventSourceImpl: options.EventSourceImpl }
      : {}),
    ...(options.schedule ? { schedule: options.schedule } : {}),
    ...(options.cancel ? { cancel: options.cancel } : {}),
    ...(options.awake !== undefined ? { awake: options.awake } : {}),
    onConnectionChange: (state) => options.store.setLink(state),
    onEvent: (frame) => {
      const outcome = options.store.apply(frame);
      if (outcome.closed) {
        control.current?.stop();
        options.onClosed?.();
      } else if (outcome.diverged) control.current?.reconnect();
    },
    ...(options.onError
      ? { onError: (error) => options.onError?.(error) }
      : {}),
  });
  control.current = stream;
  stream.start();
  return stream;
}
