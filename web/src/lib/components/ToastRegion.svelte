<script>
  import { toasts } from "$lib/toasts.js";
</script>

<div
  class="toast-container"
  aria-live="polite"
  aria-atomic="true"
  data-testid="toasts"
>
  {#each $toasts as toast (toast.id)}
    <div class="toast" role="status" data-testid="toast">{toast.message}</div>
  {/each}
</div>
