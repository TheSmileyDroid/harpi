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

  let phase = $state<"checking" | "signed-out" | "signed-in">("checking");
  let link = $state("connecting");
  let stream: { start(): void; stop(): void } | null = null;
  let probingSession = false;

  const api = createApiClient({
    onError: (error) => errorRegion.report(error),
  });

  function handleEvent(event: SseFrame) {
    if (event.type === "status") {
      appStore.applyStatus(event.data);
    } else if (event.type === "reload") {
      location.reload();
    }
  }

  async function handleConnectionChange(state: string) {
    link = state;
    if (state !== "reconnecting" || probingSession) return;
    probingSession = true;
    try {
      await api.checkSession();
    } catch (error) {
      if (error instanceof ApiError && error.status === 401) {
        stream?.stop();
        errorRegion.report(error);
        phase = "signed-out";
      }
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

  async function signIn(token: string) {
    await api.signIn(token);
    errorRegion.clear();
    phase = "signed-in";
    toasts.push("Signed in");
    await loadStatus();
    startStream();
  }

  async function boot() {
    try {
      await api.checkSession();
    } catch {
      phase = "signed-out";
      return;
    }
    phase = "signed-in";
    await loadStatus();
    startStream();
  }

  onMount(() => {
    boot();
    return () => stream?.stop();
  });
</script>

{#if phase === "checking"}
  <main class="booting" data-testid="booting">Linking…</main>
{:else if phase === "signed-out"}
  <SignIn onsignin={signIn} />
{:else}
  <StatusSurface {link} onrefresh={loadStatus} onresync={resync} {api} />
{/if}

<style>
  .booting {
    padding: 4rem 1.25rem;
    font-family: var(--font-display);
    font-weight: 600;
    letter-spacing: 0.2em;
    text-transform: uppercase;
    color: var(--color-amber-dim);
  }
</style>
