<script lang="ts">
  let {
    label,
    value,
    testid,
  }: {
    label: string;
    value: string;
    testid?: string;
  } = $props();
</script>

<span class="rating__cell">
  <span class="data-label">{label}</span>
  <span class="data-value" data-testid={testid}>{value}</span>
</span>
