<script>
  import { onMount } from 'svelte';
  import { revision } from '$lib/revision.js';

  onMount(() => {
    const events = new EventSource('/api/events');
    const reload = () => location.reload();
    events.addEventListener('reload', reload);
    return () => {
      events.removeEventListener('reload', reload);
      events.close();
    };
  });
</script>

<main id="shell">
  <h1>Harpi panel shell</h1>
  <p data-shell-revision>{revision}</p>
</main>
