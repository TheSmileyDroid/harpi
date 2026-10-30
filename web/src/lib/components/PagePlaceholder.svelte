<script lang="ts">
  let { title, note }: { title: string; note: string } = $props();
</script>

<section class="hud-panel page-placeholder" data-testid="page-placeholder">
  <h1 class="panel-label">{title}</h1>
  <p class="page-placeholder__state">
    <span class="page-placeholder__lamp" aria-hidden="true"></span>
    Em construção
  </p>
  <p class="system-note">{note}</p>
</section>

<style>
  .page-placeholder {
    min-block-size: 12rem;
  }

  .page-placeholder__state {
    display: flex;
    align-items: center;
    gap: 0.5rem;
    margin: 0;
    font-family: var(--font-label);
    font-weight: 600;
    font-size: 0.6875rem;
    line-height: 1;
    letter-spacing: 0.16em;
    text-transform: uppercase;
    color: var(--dim);
  }

  .page-placeholder__lamp {
    display: block;
    inline-size: 0.4rem;
    block-size: 0.4rem;
    background: var(--rule-strong);
  }
</style>
