<script>
  import { onMount } from "svelte";
  import { appStore } from "$lib/store.js";
  import { errorRegion } from "$lib/errors.js";
  import { toasts } from "$lib/toasts.js";
  import { createApiClient } from "$lib/api.js";
  import { createEventStream } from "$lib/sse.js";
  import SignIn from "$lib/components/SignIn.svelte";
  import StatusSurface from "$lib/components/StatusSurface.svelte";

  let phase = $state("checking");
  let link = $state("connecting");
  let stream = null;
  let probingSession = false;

  const api = createApiClient({
    onError: (error) => errorRegion.report(error),
  });

  function handleEvent(event) {
    if (event.type === "status") {
      appStore.applyStatus(event.data);
    } else if (event.type === "reload") {
      location.reload();
    }
  }

  async function handleConnectionChange(state) {
    link = state;
    if (state !== "reconnecting" || probingSession) return;
    probingSession = true;
    try {
      await api.checkSession();
    } catch (error) {
      if (error.status === 401) {
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
      onConnectionChange: handleConnectionChange,
    });
    stream.start();
  }

  async function resync() {
    await loadStatus();
    startStream();
  }

  async function loadStatus() {
    const snapshot = await api.status().catch(() => null);
    if (!snapshot) return false;
    appStore.applyStatus(snapshot);
    return true;
  }

  async function signIn(token) {
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
