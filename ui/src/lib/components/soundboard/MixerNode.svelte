<script lang="ts">
	import { Handle, Position, type NodeProps } from '@xyflow/svelte';

	// eslint-disable-next-line @typescript-eslint/no-unused-vars
	let { id: _id, data, selected }: NodeProps = $props();

	interface MixerInput {
		nodeId: string;
		label: string;
		volume: number;
	}

	const label = $derived((data?.label as string) || 'MIXER');
	const inputs = $derived((data?.inputs as MixerInput[]) || []);
	const masterVolume = $derived((data?.volume as number) ?? 100);
	const active = $derived((data?.active as boolean) ?? false);
</script>

<div class="node-mixer" class:node-selected={selected} class:node-active={active}>
	<Handle type="target" position={Position.Left} />

	<div class="node-header">
		<span class="node-type">MIX</span>
		<span class="node-title">{label}</span>
	</div>

	<div class="node-body">
		{#if inputs.length > 0}
			<div class="mixer-inputs">
				{#each inputs as input (input.nodeId)}
					<div class="mixer-input">
						<span class="input-label">{input.label}</span>
						<div class="input-meter">
							<div class="input-level" style="width: {input.volume}%"></div>
						</div>
					</div>
				{/each}
			</div>
		{:else}
			<div class="mixer-empty">NO INPUTS</div>
		{/if}

		<div class="mixer-master">
			<span class="master-label">MASTER</span>
			<span class="master-value">{masterVolume}%</span>
		</div>
	</div>

	{#if active}
		<div class="node-status active">ACTIVE</div>
	{:else}
		<div class="node-status inactive">INACTIVE</div>
	{/if}

	<Handle type="source" position={Position.Right} />
</div>

<style>
	.node-mixer {
		background: rgba(0, 0, 0, 0.85);
		border: 2px solid #005533;
		padding: 8px 12px;
		min-width: 160px;
		font-family: 'VT323', monospace;
		text-transform: uppercase;
		color: #00ff88;
		box-shadow: 0 0 6px rgba(0, 255, 136, 0.15);
	}

	.node-mixer.node-selected {
		border-color: #00ff88;
		box-shadow: 0 0 12px rgba(0, 255, 136, 0.4);
	}

	.node-mixer.node-active {
		border-color: #00ff88;
	}

	.node-header {
		display: flex;
		align-items: center;
		gap: 6px;
		border-bottom: 1px solid #003322;
		padding-bottom: 4px;
		margin-bottom: 6px;
	}

	.node-type {
		font-size: 10px;
		color: black;
		background: #00ff88;
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
		gap: 6px;
	}

	.mixer-inputs {
		display: flex;
		flex-direction: column;
		gap: 3px;
	}

	.mixer-input {
		display: flex;
		align-items: center;
		gap: 4px;
		font-size: 10px;
	}

	.input-label {
		width: 50px;
		overflow: hidden;
		text-overflow: ellipsis;
		white-space: nowrap;
		color: #005533;
	}

	.input-meter {
		flex: 1;
		height: 4px;
		background: #003322;
	}

	.input-level {
		height: 100%;
		background: #00ff88;
		transition: width 0.2s;
	}

	.mixer-empty {
		font-size: 10px;
		color: #003322;
		text-align: center;
		padding: 2px 0;
	}

	.mixer-master {
		display: flex;
		justify-content: space-between;
		font-size: 11px;
		border-top: 1px solid #003322;
		padding-top: 4px;
	}

	.master-label {
		color: #005533;
	}

	.master-value {
		color: #00ff88;
		font-weight: bold;
	}

	.node-status {
		margin-top: 4px;
		font-size: 10px;
		text-align: center;
	}

	.node-status.active {
		color: #00ff88;
	}

	.node-status.inactive {
		color: #005533;
	}
</style>
