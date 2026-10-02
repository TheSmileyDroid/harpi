<script>
  import { createDebouncer } from "$lib/debounce.js";
  import { volumeGain, volumePosition } from "$lib/transport.js";

  let {
    gain = 0,
    send,
    label = "Volume",
    sliderTestid,
    valueTestid,
    controlTestid,
    className = "volume-control",
  } = $props();

  let dragging = $state(null);
  const debouncer = createDebouncer({ delay: 300 });

  const position = $derived(dragging ?? volumePosition(gain ?? 0));
  const displayGain = $derived(volumeGain(position));

  function onInput(event) {
    dragging = Number(event.currentTarget.value);
    debouncer.run(commit);
  }

  async function commit() {
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
