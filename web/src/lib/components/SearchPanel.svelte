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
  const debouncer = createDebouncer();

  const results = $derived($appStore.search.results);
  const activeIndex = $derived($appStore.search.activeIndex);

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
      appStore.closeSearch();
      status = "idle";
      return;
    }
    if (looksLikeUrl(trimmed)) {
      appStore.closeSearch();
      status = "idle";
      debouncer.run(() => {
        if (get(appStore).search.query.trim() === trimmed) queueUrl(trimmed);
      });
      return;
    }
    appStore.openSearch();
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
</script>

<section class="hud-panel" data-testid="search-panel">
  <span class="panel-label">04 // Search</span>
  <div class="search-shell">
    <input
      class="hud-input search-input"
      type="search"
      placeholder="Search YouTube or paste a URL"
      autocomplete="off"
      aria-label="Search YouTube"
      bind:value={term}
      oninput={onInput}
      onkeydown={onKeydown}
      data-testid="search-input"
    />
    {#if $appStore.search.open}
      <div class="search-dropdown">
        {#if status === "searching"}
          <p class="search-status" data-testid="search-status">Searching…</p>
        {:else if status === "empty"}
          <p class="search-status" data-testid="search-status">No results</p>
        {:else if status === "error"}
          <p class="search-status is-alert" data-testid="search-status">
            Search failed
          </p>
        {:else}
          {#each results as track, index (track.url)}
            <div
              class="search-row"
              class:is-active={index === activeIndex}
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
        {/if}
      </div>
    {/if}
  </div>
</section>
