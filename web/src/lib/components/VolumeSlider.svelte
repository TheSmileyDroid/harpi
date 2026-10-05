<script lang="ts">
  import { createDebouncer } from "$lib/debounce";
  import { volumeGain, volumePosition } from "$lib/transport";

  let {
    gain = 0,
    send,
    label = "Volume",
    sliderTestid,
    valueTestid,
    controlTestid,
    className = "volume-control",
  }: {
    gain?: number;
    send: (value: number) => Promise<void>;
    label?: string;
    sliderTestid?: string;
    valueTestid?: string;
    controlTestid?: string;
    className?: string;
  } = $props();

  let dragging = $state<number | null>(null);
  const debouncer = createDebouncer({ delay: 300 });

  const position = $derived(dragging ?? volumePosition(gain ?? 0));
  const displayGain = $derived(volumeGain(position));

  function onInput(event: Event & { currentTarget: HTMLInputElement }) {
    dragging = Number(event.currentTarget.value);
    debouncer.run(commit);
  }

  async function commit() {
    if (dragging === null) return;
    try {
      await send(volumeGain(dragging));
    } catch {
      return;
    } finally {
      dragging = null;
    }
  }
</script>

<label class={className} data-testid={controlTestid}>
  <input
    type="range"
    class="volume-slider"
    min="0"
    max="1"
    step="0.01"
    value={position}
    oninput={onInput}
    aria-label={label}
    data-testid={sliderTestid}
  />
  <span class="volume-value" data-testid={valueTestid}>
    {displayGain.toFixed(2)}
  </span>
</label>
