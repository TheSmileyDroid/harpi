<script lang="ts">
	import Port from './Port.svelte';
	import type { SoundboardNode, PlaylistItem } from '$lib/types/soundboard';
	import { soundboardStore } from '$lib/stores/soundboard.svelte';

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

	const items = $derived((node.data?.items as PlaylistItem[]) || []);
	const currentIndex = $derived((node.data?.currentIndex as number) ?? -1);
	const playing = $derived((node.data?.playing as boolean) ?? false);
	const loop = $derived((node.data?.loop as boolean) ?? true);
	const volume = $derived((node.data?.volume as number) ?? 100);
	const progress = $derived((node.data?.progress as number) ?? 0);
	const guildId = $derived((node.data?.guildId as string) || '');

	const currentItem = $derived(
		currentIndex >= 0 && currentIndex < items.length ? items[currentIndex] : null
	);
	const totalDuration = $derived(items.reduce((sum, item) => sum + (item.duration || 0), 0));

	function formatTime(seconds: number): string {
		const mins = Math.floor(seconds / 60);
		const secs = Math.floor(seconds % 60);
		return `${mins}:${secs.toString().padStart(2, '0')}`;
	}

	const progressPct = $derived(
		currentItem && currentItem.duration > 0 ? (progress / currentItem.duration) * 100 : 0
	);

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

<div class="node-playlist" class:node-selected={selected} class:node-playing={playing}>
	<Port type="target" {onConnectStart} {onConnectEnd} />

	<div class="node-header">
		<span class="node-type">LIST</span>
		<span class="node-title">{items.length} TRACKS</span>
		<span class="node-duration">{formatTime(totalDuration)}</span>
	</div>

	<div class="node-body">
		<div class="node-tracks">
			{#each items.slice(0, 4) as item, i (i)}
				<div class="track-item" class:track-active={i === currentIndex}>
					<span class="track-index">{i + 1}.</span>
					<span class="track-title">{item.title}</span>
					<span class="track-dur">{formatTime(item.duration)}</span>
				</div>
			{/each}
			{#if items.length > 4}
				<div class="track-more">+{items.length - 4} more</div>
			{/if}
		</div>

		{#if currentItem}
			<div class="node-now-playing">
				<div class="node-time">
					{formatTime(progress)} / {formatTime(currentItem.duration)}
				</div>
				<div class="node-progress-track">
					<div class="node-progress-fill" style="width: {progressPct}%"></div>
				</div>
			</div>
		{/if}

		<div class="node-controls">
			<div class="flex items-center gap-2 flex-1">
				<span class="node-vol-label">VOL</span>
				<input
					type="range"
					min="0"
					max="200"
					step="5"
					value={volume}
					oninput={handleVolumeChange}
					class="node-vol-slider"
				/>
				<span class="node-vol-value">{volume}%</span>
			</div>
			<span class="node-loop" class:active={loop}>
				{loop ? '[LOOP]' : '[ONCE]'}
			</span>
		</div>
	</div>

	{#if playing}
		<div class="node-status playing">
			PLAYING {currentIndex + 1}/{items.length}
		</div>
	{:else}
		<div class="node-status stopped">STOPPED</div>
	{/if}

	<Port type="source" {onConnectStart} {onConnectEnd} />
</div>

<style>
	.node-playlist {
		position: relative;
		background: rgba(0, 0, 0, 0.85);
		border: 2px solid #004d80;
		padding: 8px 12px;
		min-width: 200px;
		font-family: 'VT323', monospace;
		text-transform: uppercase;
		color: #00b8ff;
		box-shadow: 0 0 6px rgba(0, 184, 255, 0.15);
	}

	.node-playlist.node-selected {
		border-color: #00b8ff;
		box-shadow: 0 0 12px rgba(0, 184, 255, 0.4);
	}

	.node-playlist.node-playing {
		border-color: #00b8ff;
	}

	.node-header {
		display: flex;
		align-items: center;
		gap: 6px;
		border-bottom: 1px solid #003355;
		padding-bottom: 4px;
		margin-bottom: 6px;
	}

	.node-type {
		font-size: 10px;
		color: black;
		background: #00b8ff;
		padding: 0 4px;
		font-weight: bold;
	}

	.node-title {
		font-size: 13px;
		font-weight: bold;
		flex: 1;
	}

	.node-duration {
		font-size: 10px;
		color: #004d80;
	}

	.node-body {
		display: flex;
		flex-direction: column;
		gap: 4px;
	}

	.node-tracks {
		display: flex;
		flex-direction: column;
		gap: 1px;
	}

	.track-item {
		display: flex;
		gap: 4px;
		font-size: 10px;
		color: #004d80;
		padding: 1px 0;
	}

	.track-item.track-active {
		color: #00b8ff;
	}

	.track-index {
		width: 16px;
		flex-shrink: 0;
	}

	.track-title {
		flex: 1;
		overflow: hidden;
		text-overflow: ellipsis;
		white-space: nowrap;
		max-width: 120px;
	}

	.track-dur {
		flex-shrink: 0;
	}

	.track-more {
		font-size: 10px;
		color: #003355;
		text-align: center;
	}

	.node-now-playing {
		margin-top: 2px;
	}

	.node-time {
		font-size: 11px;
		color: #004d80;
	}

	.node-progress-track {
		height: 4px;
		background: #003355;
		width: 100%;
	}

	.node-progress-fill {
		height: 100%;
		background: #00b8ff;
		transition: width 0.3s linear;
	}

	.node-controls {
		display: flex;
		justify-content: space-between;
		align-items: center;
		font-size: 10px;
		color: #004d80;
		gap: 8px;
	}

	.node-vol-label {
		flex-shrink: 0;
	}

	.node-vol-slider {
		-webkit-appearance: none;
		appearance: none;
		height: 4px;
		background: #003355;
		outline: none;
		flex: 1;
		width: 60px;
	}

	.node-vol-slider::-webkit-slider-thumb {
		-webkit-appearance: none;
		appearance: none;
		width: 8px;
		height: 8px;
		background: #00b8ff;
		cursor: pointer;
		border-radius: 0;
	}

	.node-vol-slider::-moz-range-thumb {
		width: 8px;
		height: 8px;
		background: #00b8ff;
		cursor: pointer;
		border-radius: 0;
		border: none;
	}

	.node-vol-value {
		min-width: 24px;
		text-align: right;
	}

	.node-loop.active {
		color: #00b8ff;
	}

	.node-status {
		margin-top: 4px;
		font-size: 10px;
		text-align: center;
	}

	.node-status.playing {
		color: #00ff88;
	}

	.node-status.stopped {
		color: #004d80;
	}
</style>
