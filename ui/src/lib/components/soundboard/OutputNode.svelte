<script lang="ts">
	import { Handle, Position, type NodeProps } from '@xyflow/svelte';

	// eslint-disable-next-line @typescript-eslint/no-unused-vars
	let { id: _id, data, selected }: NodeProps = $props();

	const connected = $derived((data?.connected as boolean) ?? false);
	const channelName = $derived((data?.channelName as string) || '---');
	const activeCount = $derived((data?.activeCount as number) ?? 0);
</script>

<div class="node-output" class:node-selected={selected} class:node-connected={connected}>
	<Handle type="target" position={Position.Left} />

	<div class="node-header">
		<span class="node-type">OUT</span>
		<span class="node-title">OUTPUT</span>
	</div>

	<div class="node-body">
		<div class="output-channel">
			<span class="channel-label">CHANNEL:</span>
			<span class="channel-name">{channelName}</span>
		</div>
		<div class="output-sources">
			<span class="sources-label">SOURCES:</span>
			<span class="sources-count">{activeCount}</span>
		</div>
	</div>

	{#if connected}
		<div class="node-status connected">CONNECTED</div>
	{:else}
		<div class="node-status disconnected">DISCONNECTED</div>
	{/if}
</div>

<style>
	.node-output {
		background: rgba(0, 0, 0, 0.85);
		border: 2px solid #660000;
		padding: 8px 12px;
		min-width: 160px;
		font-family: 'VT323', monospace;
		text-transform: uppercase;
		color: #ff4444;
		box-shadow: 0 0 6px rgba(255, 68, 68, 0.15);
	}

	.node-output.node-selected {
		border-color: #ff4444;
		box-shadow: 0 0 12px rgba(255, 68, 68, 0.4);
	}

	.node-output.node-connected {
		border-color: #ff4444;
	}

	.node-header {
		display: flex;
		align-items: center;
		gap: 6px;
		border-bottom: 1px solid #440000;
		padding-bottom: 4px;
		margin-bottom: 6px;
	}

	.node-type {
		font-size: 10px;
		color: black;
		background: #ff4444;
		padding: 0 4px;
		font-weight: bold;
	}

	.node-title {
		font-size: 13px;
		font-weight: bold;
	}

	.node-body {
		display: flex;
		flex-direction: column;
		gap: 4px;
	}

	.output-channel,
	.output-sources {
		display: flex;
		justify-content: space-between;
		font-size: 11px;
	}

	.channel-label,
	.sources-label {
		color: #660000;
	}

	.channel-name,
	.sources-count {
		color: #ff4444;
		font-weight: bold;
	}

	.node-status {
		margin-top: 4px;
		font-size: 10px;
		text-align: center;
	}

	.node-status.connected {
		color: #00ff88;
	}

	.node-status.disconnected {
		color: #660000;
	}
</style>
