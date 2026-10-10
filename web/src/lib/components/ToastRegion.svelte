<script lang="ts">
  import { toasts } from "$lib/toasts";
</script>

<div
  class="toast-container"
  aria-live="polite"
  aria-atomic="true"
  data-testid="toasts"
>
  {#each $toasts as toast (toast.id)}
    <div class="toast" role="status" data-testid="toast">
      {toast.message}
      {#if toast.action}
        <button
          type="button"
          class="hud-btn toast-action"
          onclick={toast.action.run}
          data-testid="toast-action"
        >
          {toast.action.label}
        </button>
      {/if}
    </div>
  {/each}
</div>

<style>
  .toast {
    pointer-events: auto;
    display: flex;
    align-items: center;
    gap: 0.5rem;
  }

  .toast-action {
    min-width: 0;
    padding: 0.15rem 0.5rem;
    font-size: 0.65rem;
  }
</style>
