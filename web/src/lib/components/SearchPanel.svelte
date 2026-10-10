<script lang="ts">
  import { get } from "svelte/store";
  import { appStore } from "$lib/store";
  import { toasts } from "$lib/toasts";
  import { createDebouncer } from "$lib/debounce";
  import { formatDuration } from "$lib/format";
  import type { ApiClient } from "$lib/api";
  import Thumbnail from "./Thumbnail.svelte";

  let { api }: { api: ApiClient } = $props();

  let term = $state("");
  let status = $state<"idle" | "searching" | "ready" | "empty" | "error">(
    "idle",
  );
  let busyUrl = $state<string | null>(null);
  let layerUrl = $state<string | null>(null);
  let input = $state<HTMLInputElement | null>(null);
  let dialog = $state<HTMLDialogElement | null>(null);
  const debouncer = createDebouncer();

  const open = $derived($appStore.search.open);
  const results = $derived($appStore.search.results);
  const activeIndex = $derived($appStore.search.activeIndex);
  const activeResult = $derived(results[activeIndex] ?? null);
  const showResults = $derived(status === "ready" && results.length > 0);

  async function runSearch(value: string) {
    const trimmed = value.trim();
    status = "searching";
    try {
      const payload = await api.search(trimmed);
      if (get(appStore).search.query.trim() !== trimmed) return;
      appStore.setSearchResults(payload.results);
      appStore.setActiveIndex(payload.results.length ? 0 : -1);
      status = payload.results.length ? "ready" : "empty";
    } catch {
      status = "error";
      appStore.setSearchResults([]);
    }
  }

  function resetSearch() {
    debouncer.cancel();
    appStore.setSearchQuery("");
    appStore.setSearchResults([]);
    appStore.setActiveIndex(-1);
    status = "idle";
  }

  function clearSearch() {
    term = "";
    resetSearch();
    input?.focus();
  }

  function onInput() {
    appStore.setSearchQuery(term);
    const trimmed = term.trim();
    if (!trimmed) {
      resetSearch();
      return;
    }
    debouncer.run(() => runSearch(term));
  }

  async function queueUrl(url: string) {
    busyUrl = url;
    try {
      const snapshot = await api.queue(url);
      appStore.applyStatus(snapshot);
      toasts.push("Added to queue");
      appStore.closeSearch();
    } catch {
      return;
    } finally {
      busyUrl = null;
    }
  }

  function queueTrack() {
    if (activeResult) return queueUrl(activeResult.url);
    return Promise.resolve();
  }

  async function layerTrack() {
    const track = activeResult;
    if (!track || layerUrl) return;
    layerUrl = track.url;
    try {
      const snapshot = await api.layer(track.url);
      appStore.applyStatus(snapshot);
      toasts.push("Added as layer");
      appStore.closeSearch();
    } catch {
      return;
    } finally {
      layerUrl = null;
    }
  }

  function onBackdropPointerDown(event: PointerEvent) {
    if (!dialog || event.target !== dialog) return;
    const box = dialog.getBoundingClientRect();
    const onBackdrop =
      event.clientX < box.left ||
      event.clientX > box.right ||
      event.clientY < box.top ||
      event.clientY > box.bottom;
    if (onBackdrop) appStore.closeSearch();
  }

  function onKeydown(event: KeyboardEvent) {
    if (event.key === "Escape") {
      appStore.closeSearch();
      return;
    }
    if (!results.length) return;
    if (event.key === "ArrowDown") {
      event.preventDefault();
      appStore.setActiveIndex((activeIndex + 1) % results.length);
    } else if (event.key === "ArrowUp") {
      event.preventDefault();
      appStore.setActiveIndex(
        (activeIndex - 1 + results.length) % results.length,
      );
    } else if (event.key === "Enter") {
      event.preventDefault();
      if (!activeResult) return;
      if (event.shiftKey) layerTrack();
      else queueTrack();
    }
  }

  $effect(() => {
    if (!dialog) return;
    if (open && !dialog.open) {
      dialog.showModal();
      input?.focus();
    }
    if (!open && dialog.open) dialog.close();
  });

  $effect(() => {
    if (activeIndex < 0) return;
    document
      .getElementById(`search-option-${activeIndex}`)
      ?.scrollIntoView({ block: "nearest" });
  });
</script>

<dialog
  class="palette hud-panel"
  bind:this={dialog}
  onclose={() => appStore.closeSearch()}
  onpointerdown={onBackdropPointerDown}
  aria-label="Search"
  data-testid="search-panel"
>
  <span class="panel-label">Search</span>
  <div class="search-field">
    <input
      bind:this={input}
      class="hud-input search-input"
      type="search"
      placeholder="Search YouTube or paste a URL"
      autocomplete="off"
      aria-label="Search YouTube"
      role="combobox"
      aria-expanded={showResults}
      aria-controls={showResults ? "search-results" : undefined}
      aria-activedescendant={activeIndex >= 0
        ? `search-option-${activeIndex}`
        : undefined}
      aria-autocomplete="list"
      bind:value={term}
      oninput={onInput}
      onkeydown={onKeydown}
      data-testid="search-input"
    />
    {#if term}
      <button
        type="button"
        class="search-clear"
        aria-label="Clear search"
        onclick={clearSearch}
        data-testid="search-clear"
      ></button>
    {/if}
  </div>
  {#if status === "searching"}
    <p class="search-status" role="status" data-testid="search-status">
      Searching…
    </p>
  {:else if status === "empty"}
    <p class="search-status" role="status" data-testid="search-status">
      No results — try another search.
    </p>
  {:else if status === "error"}
    <p class="search-status is-alert" role="alert" data-testid="search-status">
      Search failed
    </p>
  {:else if showResults}
    <div
      class="search-dropdown"
      role="listbox"
      id="search-results"
      aria-label="Search results"
    >
      <span class="visually-hidden" role="status" aria-live="polite">
        {results.length} results
      </span>
      {#each results as track, index (track.url)}
        <div
          class="search-row"
          class:is-active={index === activeIndex}
          role="option"
          aria-selected={index === activeIndex}
          id={`search-option-${index}`}
          tabindex="-1"
          onpointerdown={() => appStore.setActiveIndex(index)}
          data-testid="search-result"
        >
          <Thumbnail
            src={track.thumbnail}
            alt={track.title}
            className="search-thumb"
          />
          <span class="data-title">{track.title}</span>
          <span class="row-meta">
            {track.uploader} · {formatDuration(track.duration)}
          </span>
        </div>
      {/each}
    </div>
    <div class="search-actions" data-testid="search-actions">
      <span class="search-selection">
        <span class="data-label">Selected</span>
        <span
          class="data-value"
          class:is-empty={!activeResult}
          data-testid="search-selection"
        >
          {activeResult ? activeResult.title : "No track selected"}
        </span>
      </span>
      <span class="search-buttons">
        <button
          type="button"
          class="hud-btn"
          onclick={queueTrack}
          disabled={!activeResult || busyUrl !== null}
          data-testid="queue-track"
        >
          Queue
        </button>
        <button
          type="button"
          class="hud-btn"
          onclick={layerTrack}
          disabled={!activeResult || layerUrl !== null}
          data-testid="layer-track"
        >
          Layer
        </button>
      </span>
    </div>
  {/if}
</dialog>

<style>
  .palette {
    width: min(42rem, calc(100vw - 2rem));
    margin: 12vh auto auto;
  }

  .palette::backdrop {
    background: rgb(0 0 0 / 0.6);
  }

  .palette .search-input {
    width: 100%;
    padding-inline-end: 2rem;
  }

  .palette .search-input::-webkit-search-cancel-button,
  .palette .search-input::-webkit-search-decoration {
    appearance: none;
    display: none;
  }

  .search-field {
    position: relative;
  }

  .search-clear {
    position: absolute;
    inset-block-start: 50%;
    inset-inline-end: 0.35rem;
    inline-size: 1.4rem;
    block-size: 1.4rem;
    padding: 0;
    background: none;
    border: none;
    color: var(--color-amber-dim);
    cursor: pointer;
    translate: 0 -50%;
  }

  .search-clear::before,
  .search-clear::after {
    content: "";
    position: absolute;
    inset: 0;
    margin: auto;
    inline-size: 0.8rem;
    block-size: 1px;
    background: currentColor;
  }

  .search-clear::before {
    transform: rotate(45deg);
  }

  .search-clear::after {
    transform: rotate(-45deg);
  }

  .search-clear:hover {
    color: var(--color-amber-bright);
  }

  .search-clear:focus-visible {
    outline: 1px solid var(--color-amber-bright);
    outline-offset: 2px;
  }

  .palette .search-dropdown {
    margin-top: 0.5rem;
    max-height: 60vh;
    overflow-y: auto;
  }

  .search-actions {
    display: flex;
    flex-wrap: wrap;
    align-items: center;
    justify-content: space-between;
    gap: 0.5rem;
    margin-top: 0.5rem;
  }

  .search-selection {
    display: flex;
    align-items: center;
    gap: 0.5rem;
    min-width: 0;
  }

  .search-selection .data-label {
    flex: none;
    inline-size: auto;
  }

  .search-selection .data-value {
    min-width: 0;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
    font-size: 0.8rem;
  }

  .search-buttons {
    display: flex;
    flex: none;
    gap: 0.35rem;
  }
</style>
