<script lang="ts">
  import "../app.css";
  import ErrorRegion from "$lib/components/ErrorRegion.svelte";
  import ToastRegion from "$lib/components/ToastRegion.svelte";
  import type { Snippet } from "svelte";

  let { children }: { children: Snippet } = $props();
</script>

<ErrorRegion />
{@render children()}
<ToastRegion />
