<script lang="ts">
  import { createDebouncer } from "$lib/debounce";
  import { volumeGain, volumePosition } from "$lib/transport";
  import { formatVolume } from "$lib/format";

  // Wait for the drag to settle before sending, so one gesture is one request.
  const VOLUME_DEBOUNCE_MS = 300;

  let {
    gain = 0,
    send,
    label = "Volume",
    disabled = false,
    sliderTestid,
    valueTestid,
    controlTestid,
    className = "volume-control",
  }: {
    gain?: number;
    send: (value: number) => Promise<void>;
    label?: string;
    disabled?: boolean;
    sliderTestid?: string;
    valueTestid?: string;
    controlTestid?: string;
    className?: string;
  } = $props();

  let dragging = $state<number | null>(null);
  const debouncer = createDebouncer(VOLUME_DEBOUNCE_MS);

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
    {disabled}
    data-testid={sliderTestid}
  />
  <span class="volume-value" data-testid={valueTestid}>
    {formatVolume(displayGain)}
  </span>
</label>
