<script lang="ts">
	import Port from './Port.svelte';
	import type { SoundboardNode } from '$lib/types/soundboard';
	import { soundboardStore } from '$lib/stores/soundboard.svelte';
	import { guildStore } from '$lib/stores/guild.svelte';

	interface ConnectEvent {
		type: 'target' | 'source';
		event: MouseEvent;
		element: HTMLElement;
	}

	interface Props {
		node: SoundboardNode;
		selected?: boolean;
		onConnectStart?: (detail: ConnectEvent) => void;
		onConnectEnd?: (detail: ConnectEvent) => void;
	}

	let { node, selected = false, onConnectStart, onConnectEnd }: Props = $props();

	const guildId = $derived(guildStore.current?.id);

	interface MixerInput {
		nodeId: string;
		label: string;
		volume: number;
	}

	const label = $derived((node.data?.label as string) || 'MIXER');
	const inputs = $derived((node.data?.inputs as MixerInput[]) || []);
	const masterVolume = $derived((node.data?.volume as number) ?? 100);
	const active = $derived((node.data?.active as boolean) ?? false);

	async function handleVolumeChange(e: Event) {
		const target = e.target as HTMLInputElement;
		const newVolume = parseInt(target.value);
		
		// Optimistic update
		soundboardStore.updateNode(node.id, { volume: newVolume });

		if (!guildId) return;

		try {
			const res = await fetch('/api/soundboard/node/volume', {
				method: 'POST',
				headers: { 'Content-Type': 'application/json' },
				body: JSON.stringify({
					guild_id: guildId,
					node_id: node.id,
					volume: newVolume
				})
			});
			if (!res.ok) {
				console.error('Failed to update volume');
			}
		} catch (e) {
			console.error('Volume update error:', e);
		}
	}
</script>

<div class="node-mixer" class:node-selected={selected} class:node-active={active}>
	<Port type="target" {onConnectStart} {onConnectEnd} />

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
			<div class="flex items-center gap-2 flex-1">
				<input
					type="range"
					min="0"
					max="200"
					step="5"
					value={masterVolume}
					oninput={handleVolumeChange}
					class="node-vol-slider"
				/>
				<span class="master-value">{masterVolume}%</span>
			</div>
		</div>
	</div>

	{#if active}
		<div class="node-status active">ACTIVE</div>
	{:else}
		<div class="node-status inactive">INACTIVE</div>
	{/if}

	<Port type="source" {onConnectStart} {onConnectEnd} />
</div>

<style>
	.node-mixer {
		position: relative;
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
		align-items: center;
		gap: 8px;
		font-size: 11px;
		border-top: 1px solid #003322;
		padding-top: 4px;
	}

	.master-label {
		color: #005533;
		flex-shrink: 0;
	}

	.master-value {
		color: #00ff88;
		font-weight: bold;
		min-width: 24px;
		text-align: right;
	}

	.node-vol-slider {
		-webkit-appearance: none;
		appearance: none;
		height: 4px;
		background: #003322;
		outline: none;
		flex: 1;
		width: 60px;
	}

	.node-vol-slider::-webkit-slider-thumb {
		-webkit-appearance: none;
		appearance: none;
		width: 8px;
		height: 8px;
		background: #00ff88;
		cursor: pointer;
		border-radius: 0;
	}

	.node-vol-slider::-moz-range-thumb {
		width: 8px;
		height: 8px;
		background: #00ff88;
		cursor: pointer;
		border-radius: 0;
		border: none;
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



