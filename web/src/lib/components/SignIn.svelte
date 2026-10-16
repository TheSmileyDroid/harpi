<script lang="ts">
  let { onsignin }: { onsignin: (token: string) => Promise<void> } = $props();
  let token = $state("");
  let busy = $state(false);
  let invalid = $state(false);

  async function submit(event: Event) {
    event.preventDefault();
    busy = true;
    invalid = false;
    try {
      await onsignin(token);
    } catch {
      invalid = true;
    } finally {
      busy = false;
    }
  }
</script>

<main class="signin" data-testid="signin">
  <form class="hud-panel signin-panel" onsubmit={submit}>
    <span class="panel-label">Access</span>
    <p class="page-title signin-title">HARPI PANEL</p>
    <p class="signin-note">
      Enter the panel token. The self-hoster sets it as PANEL_TOKEN.
    </p>
    <div class="data-row">
      <label class="data-label" for="panel-token">Panel token</label>
      <input
        class="visually-hidden"
        type="text"
        name="username"
        autocomplete="username"
        tabindex="-1"
        aria-hidden="true"
      />
      <input
        id="panel-token"
        class="hud-input"
        type="password"
        autocomplete="current-password"
        aria-invalid={invalid}
        bind:value={token}
        data-testid="panel-token"
      />
    </div>
    <button
      class="hud-btn signin-submit"
      type="submit"
      disabled={busy}
      data-testid="sign-in"
    >
      {busy ? "CHECKING…" : "ENTER"}
    </button>
  </form>
</main>

<style>
  .signin {
    display: flex;
    justify-content: center;
    padding: 4rem 1.25rem;
  }

  .signin-panel {
    width: min(28rem, 100%);
  }

  @media (prefers-reduced-motion: no-preference) {
    .signin-panel {
      animation: plate-rise var(--motion-settle) var(--ease-arrive);
    }
  }

  .signin-title {
    font-size: 1rem;
    margin-bottom: 0.5rem;
  }

  .signin-note {
    margin: 0 0 0.85rem;
    font-size: 0.7rem;
    letter-spacing: 0.04em;
    color: var(--ink-dim);
  }

  .data-row {
    margin-bottom: 0.85rem;
  }

  .data-row .hud-input {
    flex: 1;
    min-width: 8rem;
  }

  .signin-submit {
    width: 100%;
  }
</style>
