<script lang="ts">
  let { online }: { online: boolean } = $props();
</script>

<span
  class={online ? "bot-online" : "bot-offline"}
  data-testid="bot-status"
  data-online={online}
>
  <span class="bot-lamp" class:blink={!online} aria-hidden="true"></span>
  {online ? "ONLINE" : "OFFLINE"}
</span>
