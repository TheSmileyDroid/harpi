<script lang="ts">
  import { onMount } from "svelte";
  import { resolve } from "$app/paths";
  import { page } from "$app/state";
  import { createEventStream } from "$lib/sse";
  import {
    SHELL_PAGES,
    campaignDisplayName,
    isShellPageActive,
    shellLinkLabel,
  } from "$lib/shell";
  import type { ShellLinkState } from "$lib/shell";
  import type { Snippet } from "svelte";

  let { children }: { children: Snippet } = $props();

  let link = $state<ShellLinkState>("connecting");
  let stream: { start(): void; stop(): void } | null = null;

  const campaign = $derived(page.params.campaign ?? "");
  const campaignName = $derived(campaignDisplayName(campaign));
  const pathname = $derived(page.url.pathname);

  onMount(() => {
    document.documentElement.style.setProperty("--transport-height", "0rem");
    stream = createEventStream({
      onConnectionChange: (state) => {
        link =
          state === "connected" || state === "reconnecting"
            ? state
            : "connecting";
      },
    });
    stream.start();
    return () => {
      document.documentElement.style.removeProperty("--transport-height");
      stream?.stop();
      stream = null;
    };
  });
</script>

<svelte:head>
  <title>{campaignName} — Harpi</title>
</svelte:head>

<div class="shell" data-testid="shell">
  <aside
    class="shell__rail"
    aria-label="Navegação da campanha"
    data-testid="shell-rail"
  >
    <a
      class="shell__brand"
      href={resolve("/", {})}
      data-testid="shell-wordmark"
    >
      <img
        class="shell__mark"
        src="/brand/harpi-smiley-mark.svg"
        alt=""
        aria-hidden="true"
      />
      <span class="shell__wordmark">Harpi</span>
    </a>

    <div class="shell__campaign placard" data-testid="shell-campaign">
      <span class="placard__label">Campanha</span>
      <span class="placard__value">{campaignName}</span>
    </div>

    <nav class="shell__pages" aria-label="Páginas da campanha">
      {#each SHELL_PAGES as item (item.slug)}
        <a
          class="shell__page"
          href={resolve(item.route, { campaign })}
          aria-current={isShellPageActive(pathname, item.slug)
            ? "page"
            : undefined}
          data-testid={`shell-page-${item.slug}`}
        >
          <span class="shell__lamp" aria-hidden="true"></span>
          {item.label}
        </a>
      {/each}
    </nav>

    <div class="shell__link placard" data-testid="shell-link">
      <span class="placard__label">Link</span>
      <span class="link-state" data-link={link} data-testid="shell-link-state">
        {shellLinkLabel(link)}
      </span>
    </div>
  </aside>

  <main class="shell__main" data-testid="shell-main">
    {@render children()}
  </main>
</div>

<style>
  .shell {
    min-block-size: 100vh;
    background: var(--ground);
  }

  .shell__rail {
    display: flex;
    align-items: center;
    flex-wrap: wrap;
    gap: 0.5rem;
    padding: 0.5rem 0.75rem;
    background: var(--plate);
    border-block-end: 1px solid var(--rule-strong);
  }

  .shell__brand {
    display: flex;
    align-items: center;
    gap: 0.55rem;
    color: var(--sand);
    text-decoration: none;
    border-radius: var(--radius-key);
  }

  .shell__brand:focus-visible {
    outline: 2px solid var(--amber);
    outline-offset: 2px;
  }

  .shell__mark {
    display: block;
    block-size: 1.6rem;
    inline-size: auto;
    image-rendering: pixelated;
  }

  .shell__wordmark {
    font-family: var(--font-display);
    font-weight: 800;
    font-size: 0.85rem;
    line-height: 1;
    letter-spacing: 0.24em;
    text-transform: uppercase;
  }

  .shell__campaign {
    flex-direction: column;
    align-items: flex-start;
    gap: 0.3rem;
    padding-block: 0.5rem;
  }

  .shell__campaign .placard__value {
    max-inline-size: 12rem;
  }

  .shell__pages {
    display: flex;
    flex-wrap: wrap;
    gap: 0.35rem;
    min-inline-size: 0;
  }

  .shell__page {
    display: flex;
    align-items: center;
    gap: 0.5rem;
    min-block-size: 2.5rem;
    padding: 0.65rem 0.6rem;
    border: 1px solid transparent;
    border-radius: var(--radius-key);
    color: var(--dim);
    font-family: var(--font-label);
    font-weight: 600;
    font-size: 0.72rem;
    line-height: 1;
    letter-spacing: 0.14em;
    text-transform: uppercase;
    text-decoration: none;
    transition:
      color var(--motion-quick) ease,
      background-color var(--motion-quick) ease,
      border-color var(--motion-quick) ease;
  }

  .shell__page:hover {
    color: var(--sand);
    background: var(--plate-2);
    border-color: var(--oxide);
  }

  .shell__page:focus-visible {
    outline: 2px solid var(--amber);
    outline-offset: 2px;
  }

  .shell__page[aria-current="page"] {
    color: var(--sand);
    background: var(--plate-2);
  }

  .shell__lamp {
    display: block;
    inline-size: 0.4rem;
    block-size: 0.4rem;
    background: var(--rule-strong);
  }

  .shell__page[aria-current="page"] .shell__lamp {
    background: var(--amber);
  }

  .shell__link {
    margin-inline-start: auto;
  }

  .shell__main {
    max-inline-size: 72rem;
    inline-size: 100%;
    margin-inline: auto;
    padding: 0.75rem 1.25rem 2rem;
    min-inline-size: 0;
  }

  @media (min-width: 56rem) {
    .shell {
      display: grid;
      grid-template-columns: 14rem minmax(0, 1fr);
    }

    .shell__rail {
      position: fixed;
      inset-block: 0;
      inset-inline-start: 0;
      inline-size: 14rem;
      flex-direction: column;
      flex-wrap: nowrap;
      align-items: stretch;
      gap: 1rem;
      padding: 1rem;
      border-block-end: none;
      border-inline-end: 1px solid var(--rule-strong);
      overflow-y: auto;
    }

    .shell__campaign {
      align-self: stretch;
      padding-block: 0.4rem;
    }

    .shell__pages {
      flex-direction: column;
      flex-wrap: nowrap;
      gap: 0;
    }

    .shell__page + .shell__page {
      border-block-start: 1px solid var(--rule);
    }

    .shell__link {
      margin-inline-start: 0;
      margin-block-start: auto;
      align-self: stretch;
    }

    .shell__main {
      grid-column: 2;
    }
  }
</style>
