<script lang="ts">
  import { onMount } from "svelte";
  import { appStore } from "$lib/store";
  import { errorRegion } from "$lib/errors";
  import { toasts } from "$lib/toasts";
  import { ApiError, createApiClient } from "$lib/api";
  import { createEventStream } from "$lib/sse";
  import type { SseFrame } from "$lib/sse";
  import SignIn from "$lib/components/SignIn.svelte";
  import StatusSurface from "$lib/components/StatusSurface.svelte";

  const AUTH_MESSAGES: Record<string, string> = {
    unconfigured: "Discord sign-in is not configured on this server",
    cancelled: "Discord sign-in was cancelled",
    denied: "That Discord account shares no server with Harpi",
    unavailable: "Harpi could not verify your servers right now",
    failed: "Discord sign-in failed",
  };

  let phase = $state<"checking" | "signed-out" | "signed-in">("checking");
  let link = $state("connecting");
  let stale = $state(false);
  let stream: { start(): void; stop(): void } | null = null;
  let probingSession = false;
  let lastDataAt = Date.now();

  const STALE_AFTER_MS = 15000;
  const STALE_CHECK_MS = 1000;

  const api = createApiClient({
    onError: handleApiError,
  });

  function handleApiError(error: unknown) {
    endSessionIfUnauthorized(error);
    errorRegion.report(error);
  }

  function endSessionIfUnauthorized(error: unknown): boolean {
    if (!(error instanceof ApiError) || error.status !== 401) return false;
    stream?.stop();
    phase = "signed-out";
    return true;
  }

  function reportAuthResult() {
    const reason = new URLSearchParams(location.search).get("auth");
    if (!reason) return;
    history.replaceState(null, "", location.pathname);
    const message = AUTH_MESSAGES[reason];
    if (message) errorRegion.report({ code: reason, message });
  }

  function handleEvent(event: SseFrame) {
    if (event.type === "reload") {
      location.reload();
      return;
    }
    appStore.applySse(event);
    if (
      event.type === "status" ||
      event.type === "position" ||
      event.type === "directory"
    ) {
      lastDataAt = Date.now();
      stale = false;
    }
  }

  async function handleConnectionChange(state: string) {
    const previous = link;
    link = state;
    if (state === "reconnecting") {
      stale = true;
    }
    if (state === "connected" && previous === "reconnecting") {
      lastDataAt = Date.now();
      stale = false;
      await loadStatus();
    }
    if (state !== "reconnecting" || probingSession) return;
    probingSession = true;
    try {
      await api.checkSession();
    } catch (error) {
      if (endSessionIfUnauthorized(error)) errorRegion.report(error);
    } finally {
      probingSession = false;
    }
  }

  function startStream() {
    stream?.stop();
    stream = createEventStream({
      onEvent: handleEvent,
      onError: (error) => errorRegion.report(error),
      onConnectionChange: handleConnectionChange,
    });
    stream.start();
  }

  async function resync() {
    await loadStatus();
    startStream();
  }

  async function loadStatus(): Promise<boolean> {
    const snapshot = await api.status().catch(() => null);
    if (!snapshot) return false;
    appStore.applyStatus(snapshot);
    return true;
  }

  async function signOut() {
    stream?.stop();
    stream = null;
    await api.logout().catch(() => null);
    appStore.reset();
    errorRegion.clear();
    phase = "signed-out";
    toasts.push("Signed out");
  }

  async function boot() {
    try {
      await api.checkSession();
    } catch {
      reportAuthResult();
      phase = "signed-out";
      return;
    }
    phase = "signed-in";
    await loadStatus();
    startStream();
  }

  function resumeWhenVisible() {
    if (phase !== "signed-in") return;
    if (stale || link !== "connected") void resync();
  }

  onMount(() => {
    boot();
    const freshness = setInterval(() => {
      if (phase !== "signed-in") return;
      stale = link !== "connected" || Date.now() - lastDataAt > STALE_AFTER_MS;
    }, STALE_CHECK_MS);
    const onVisibility = () => {
      if (document.visibilityState === "visible") resumeWhenVisible();
    };
    document.addEventListener("visibilitychange", onVisibility);
    window.addEventListener("online", resumeWhenVisible);
    return () => {
      clearInterval(freshness);
      document.removeEventListener("visibilitychange", onVisibility);
      window.removeEventListener("online", resumeWhenVisible);
      stream?.stop();
    };
  });
</script>

{#if phase === "checking"}
  <main class="booting" data-testid="booting">
    <img
      class="booting__mark blink"
      src="/brand/harpi-smiley-mark.svg"
      alt=""
      aria-hidden="true"
    />
    <span>Linking…</span>
  </main>
{:else if phase === "signed-out"}
  <SignIn loginUrl={api.loginUrl} />
{:else}
  <StatusSurface
    {link}
    {stale}
    onrefresh={loadStatus}
    onresync={resync}
    onsignout={signOut}
    {api}
  />
{/if}

<style>
  .booting {
    display: flex;
    align-items: center;
    gap: 0.6rem;
    padding: 4rem 1.25rem;
    font-family: var(--font-display);
    font-weight: 700;
    font-size: 0.85rem;
    letter-spacing: 0.2em;
    text-transform: uppercase;
    color: var(--dim);
  }

  .booting__mark {
    display: block;
    height: 38px;
    width: auto;
    image-rendering: pixelated;
  }
</style>
