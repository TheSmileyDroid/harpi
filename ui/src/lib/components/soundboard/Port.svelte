<script lang="ts">
	interface ConnectEvent {
		type: 'target' | 'source';
		event: MouseEvent;
		element: HTMLElement;
	}

	interface Props {
		type: 'target' | 'source';
		position?: 'left' | 'right' | 'top' | 'bottom';
		onConnectStart?: (detail: ConnectEvent) => void;
		onConnectEnd?: (detail: ConnectEvent) => void;
	}

	let {
		type,
		position = type === 'target' ? 'left' : 'right',
		onConnectStart,
		onConnectEnd
	}: Props = $props();

	let el: HTMLElement;

	function handleMouseDown(e: MouseEvent) {
		// Stop propagation so we don't drag the node
		e.stopPropagation();
		if (onConnectStart) {
			onConnectStart({ type, event: e, element: el });
		}
	}

	function handleMouseUp(e: MouseEvent) {
		e.stopPropagation();
		if (onConnectEnd) {
			onConnectEnd({ type, event: e, element: el });
		}
	}
</script>

<!-- svelte-ignore a11y_no_static_element_interactions -->
<div
	bind:this={el}
	class="port {type} {position}"
	onmousedown={handleMouseDown}
	onmouseup={handleMouseUp}
></div>

<style>
	.port {
		position: absolute;
		width: 10px;
		height: 10px;
		background: var(--color-retro-primary);
		border: 1px solid var(--color-retro-dim);
		z-index: 10;
		cursor: crosshair;
	}

	.port:hover {
		background: var(--color-retro-bg);
		border-color: var(--color-retro-primary);
	}

	.port.left {
		left: -5px;
		top: 50%;
		transform: translateY(-50%);
	}

	.port.right {
		right: -5px;
		top: 50%;
		transform: translateY(-50%);
	}
</style>
