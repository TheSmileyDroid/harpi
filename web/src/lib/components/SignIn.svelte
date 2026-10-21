<script lang="ts">
  let { loginUrl }: { loginUrl: string } = $props();

  function begin() {
    window.location.assign(loginUrl);
  }
</script>

<main class="signin" data-testid="signin">
  <div class="hud-panel signin-panel" data-testid="signin-panel">
    <span class="panel-label">Access</span>
    <p class="page-title signin-title">HARPI PANEL</p>
    <p class="signin-note">
      Sign in with Discord. You must share a server with Harpi to enter.
    </p>
    <button
      type="button"
      class="hud-btn hud-btn--primary signin-submit"
      onclick={begin}
      data-testid="sign-in"
    >
      CONTINUE WITH DISCORD
    </button>
  </div>
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
    font-family: var(--font-label);
    font-size: 0.75rem;
    letter-spacing: 0.02em;
    color: var(--dim);
  }

  .signin-submit {
    display: block;
    width: 100%;
    text-align: center;
  }
</style>
