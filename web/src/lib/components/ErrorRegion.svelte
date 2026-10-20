<script lang="ts">
  import { errorRegion } from "$lib/errors";
</script>

{#if $errorRegion.length}
  <div class="error-region" data-testid="error-region">
    {#each $errorRegion as error (error.id)}
      <p class="panel-error" role="alert">
        <span class="stamp is-hazard">Hazard</span>
        <span data-testid="error-message">{error.message}</span>
        {#if error.code === "contract_violation"}
          <button
            class="hud-btn"
            type="button"
            onclick={() => location.reload()}
            data-testid="error-refresh"
          >
            Refresh
          </button>
        {/if}
        <button
          class="hud-btn"
          type="button"
          onclick={() => errorRegion.dismiss(error.id)}
          data-testid="error-dismiss"
        >
          Dismiss
        </button>
      </p>
    {/each}
  </div>
{/if}

<style>
  .panel-error [data-testid="error-message"] {
    flex: 1;
    min-width: 0;
  }
</style>
