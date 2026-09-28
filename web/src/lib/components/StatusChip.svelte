<script>
  let { online } = $props();
</script>

<span
  class={online ? "bot-online" : "bot-offline blink"}
  data-testid="bot-status"
  data-online={online}
>
  {online ? "ONLINE" : "OFFLINE"}
</span>
