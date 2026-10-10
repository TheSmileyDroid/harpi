<script lang="ts">
  import { get } from "svelte/store";
  import { appStore } from "$lib/store";
  import { toasts } from "$lib/toasts";
  import { createDebouncer } from "$lib/debounce";
  import { formatDuration } from "$lib/format";
  import { looksLikeUrl } from "$lib/url";
  import type { ApiClient } from "$lib/api";
  import type { Track } from "$lib/contract/panel.gen";
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
  const showResults = $derived(status === "ready" && results.length > 0);

  async function runSearch(value: string) {
    const trimmed = value.trim();
    status = "searching";
    try {
      const payload = await api.search(trimmed);
      if (get(appStore).search.query.trim() !== trimmed) return;
      appStore.setSearchResults(payload.results);
      appStore.setActiveIndex(-1);
      status = payload.results.length ? "ready" : "empty";
    } catch {
      status = "error";
      appStore.setSearchResults([]);
    }
  }

  function onInput() {
    appStore.setSearchQuery(term);
    const trimmed = term.trim();
    if (!trimmed) {
      debouncer.cancel();
      appStore.setSearchResults([]);
      status = "idle";
      return;
    }
    if (looksLikeUrl(trimmed)) {
      status = "idle";
      debouncer.run(() => {
        if (get(appStore).search.query.trim() === trimmed) queueUrl(trimmed);
      });
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

  function queueTrack(track: Track) {
    return queueUrl(track.url);
  }

  async function layerTrack(track: Track) {
    if (layerUrl) return;
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
      const track = results[activeIndex];
      if (track) queueTrack(track);
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
</script>

<dialog
  class="palette hud-panel"
  bind:this={dialog}
  onclose={() => appStore.closeSearch()}
  onclick={(event) => {
    if (event.target === dialog) appStore.closeSearch();
  }}
  aria-label="Search"
  data-testid="search-panel"
>
  <span class="panel-label">Search</span>
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
          <button
            type="button"
            class="hud-btn"
            onclick={() => queueTrack(track)}
            disabled={busyUrl === track.url}
            data-testid="queue-track"
          >
            Queue
          </button>
          <button
            type="button"
            class="hud-btn"
            onclick={() => layerTrack(track)}
            disabled={layerUrl === track.url}
            data-testid="layer-track"
          >
            Layer
          </button>
        </div>
      {/each}
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
  }

  .palette .search-dropdown {
    margin-top: 0.5rem;
    max-height: 60vh;
    overflow-y: auto;
  }
</style>
