<script lang="ts">
  import { errorRegion } from "$lib/errors";
</script>

{#if $errorRegion.length}
  <div class="error-region" data-testid="error-region">
    {#each $errorRegion as error (error.id)}
      <p class="panel-error" role="alert">
        <span data-testid="error-message">{error.message}</span>
        <button
          class="hud-btn dismiss"
          type="button"
          onclick={() => errorRegion.dismiss(error.id)}
        >
          Dismiss
        </button>
      </p>
    {/each}
  </div>
{/if}

<style>
  .dismiss {
    min-width: 0;
    padding: 0.2rem 0.5rem;
  }
</style>
