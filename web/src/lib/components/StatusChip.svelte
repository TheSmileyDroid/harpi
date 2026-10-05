<script lang="ts">
  let { online }: { online: boolean } = $props();
</script>

<span
  class={online ? "bot-online" : "bot-offline blink"}
  data-testid="bot-status"
  data-online={online}
>
  {online ? "ONLINE" : "OFFLINE"}
</span>
