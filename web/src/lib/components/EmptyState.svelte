<script lang="ts">
  let {
    message,
    testid,
    buttonTestid,
    onsearch,
  }: {
    message: string;
    testid: string;
    buttonTestid: string;
    onsearch: () => void;
  } = $props();
</script>

<div class="empty-state">
  <p class="data-value is-empty" data-testid={testid}>{message}</p>
  <button
    type="button"
    class="hud-btn"
    onclick={onsearch}
    data-testid={buttonTestid}
  >
    Search
  </button>
</div>
