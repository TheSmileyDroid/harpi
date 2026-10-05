<script lang="ts">
  import "../app.css";
  import ErrorRegion from "$lib/components/ErrorRegion.svelte";
  import ToastRegion from "$lib/components/ToastRegion.svelte";
  import type { Snippet } from "svelte";

  let { children }: { children: Snippet } = $props();
</script>

<div class="error-slot">
  <ErrorRegion />
</div>
{@render children()}
<ToastRegion />

<style>
  .error-slot {
    max-width: 72rem;
    margin: 0 auto;
    padding: 0.5rem 1.25rem 0;
  }
</style>
