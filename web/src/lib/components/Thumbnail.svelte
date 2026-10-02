<script>
  let { src = "", alt = "", className = "search-thumb", size = 48 } = $props();
</script>

{#if src}
  <img
    class={className}
    {src}
    {alt}
    width={size}
    height={size}
    loading="lazy"
  />
{:else}
  <span class="{className} thumb-empty" aria-hidden="true"></span>
{/if}
