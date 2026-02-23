<script lang="ts">
	import { Handle, Position, type NodeProps } from '@xyflow/svelte';

	let { id, data, selected }: NodeProps = $props();

	const title = $derived((data?.title as string) || 'UNTITLED');
	const url = $derived((data?.url as string) || '');
	const duration = $derived((data?.duration as number) || 0);
	const volume = $derived((data?.volume as number) ?? 100);
	const loop = $derived((data?.loop as boolean) ?? true);
	const playing = $derived((data?.playing as boolean) ?? false);
	const progress = $derived((data?.progress as number) ?? 0);
	const guildId = $derived((data?.guildId as string) || '');

	let loading = $state(false);
	let error = $state('');

	function formatTime(seconds: number): string {
		const mins = Math.floor(seconds / 60);
		const secs = Math.floor(seconds % 60);
		return `${mins}:${secs.toString().padStart(2, '0')}`;
	}

	const progressPct = $derived(duration > 0 ? (progress / duration) * 100 : 0);

	async function togglePlayback() {
		if (!guildId || !url || loading) return;
		loading = true;
		error = '';

		try {
			if (playing) {
				const res = await fetch('/api/soundboard/node/stop', {
					method: 'POST',
					headers: { 'Content-Type': 'application/json' },
					body: JSON.stringify({ guild_id: guildId, node_id: id })
				});
				if (!res.ok) {
					const err = await res.json();
					throw new Error(err.error || 'Failed to stop');
				}
			} else {
				const res = await fetch('/api/soundboard/node/start', {
					method: 'POST',
					headers: { 'Content-Type': 'application/json' },
					body: JSON.stringify({
						guild_id: guildId,
						node_id: id,
						url,
						volume,
						loop
					})
				});
				if (!res.ok) {
					const err = await res.json();
					throw new Error(err.error || 'Failed to start');
				}
			}
		} catch (e: unknown) {
			error = e instanceof Error ? e.message : 'Unknown error';
		} finally {
			loading = false;
		}
	}
</script>

<div class="node-sound-source" class:node-selected={selected} class:node-playing={playing}>
	<Handle type="target" position={Position.Left} />

	<div class="node-header">
		<span class="node-type">SRC</span>
		<span class="node-title">{title}</span>
	</div>

	<div class="node-body">
		{#if duration > 0}
			<div class="node-time">
				{formatTime(progress)} / {formatTime(duration)}
			</div>
			<div class="node-progress-track">
				<div class="node-progress-fill" style="width: {progressPct}%"></div>
			</div>
		{/if}
		<div class="node-controls">
			<span class="node-vol">VOL: {volume}%</span>
			<span class="node-loop" class:active={loop}>
				{loop ? '[LOOP]' : '[ONCE]'}
			</span>
		</div>
	</div>

	<button
		class="node-play-btn"
		class:playing
		disabled={loading || !guildId || !url}
		onclick={togglePlayback}
	>
		{#if loading}
			[...]
		{:else if playing}
			[ STOP ]
		{:else}
			[ PLAY ]
		{/if}
	</button>

	{#if error}
		<div class="node-error">{error}</div>
	{/if}

	{#if playing}
		<div class="node-status playing">PLAYING</div>
	{:else}
		<div class="node-status stopped">STOPPED</div>
	{/if}

	<Handle type="source" position={Position.Right} />
</div>

<style>
	.node-sound-source {
		background: rgba(0, 0, 0, 0.85);
		border: 2px solid var(--color-retro-dim);
		padding: 8px 12px;
		min-width: 180px;
		font-family: 'VT323', monospace;
		text-transform: uppercase;
		color: var(--color-retro-primary);
		box-shadow: 0 0 6px rgba(255, 184, 0, 0.15);
	}

	.node-sound-source.node-selected {
		border-color: var(--color-retro-primary);
		box-shadow: 0 0 12px rgba(255, 184, 0, 0.4);
	}

	.node-sound-source.node-playing {
		border-color: var(--color-retro-primary);
	}

	.node-header {
		display: flex;
		align-items: center;
		gap: 6px;
		border-bottom: 1px solid var(--color-retro-off);
		padding-bottom: 4px;
		margin-bottom: 6px;
	}

	.node-type {
		font-size: 10px;
		color: var(--color-retro-bg);
		background: var(--color-retro-primary);
		padding: 0 4px;
		font-weight: bold;
	}

	.node-title {
		font-size: 13px;
		font-weight: bold;
		overflow: hidden;
		text-overflow: ellipsis;
		white-space: nowrap;
		max-width: 140px;
	}

	.node-body {
		display: flex;
		flex-direction: column;
		gap: 4px;
	}

	.node-time {
		font-size: 11px;
		color: var(--color-retro-dim);
	}

	.node-progress-track {
		height: 4px;
		background: var(--color-retro-off);
		width: 100%;
	}

	.node-progress-fill {
		height: 100%;
		background: var(--color-retro-primary);
		transition: width 0.3s linear;
	}

	.node-controls {
		display: flex;
		justify-content: space-between;
		font-size: 10px;
		color: var(--color-retro-dim);
	}

	.node-loop.active {
		color: var(--color-retro-primary);
	}

	.node-play-btn {
		display: block;
		width: 100%;
		margin-top: 6px;
		padding: 3px 0;
		border: 1px solid var(--color-retro-dim);
		background: transparent;
		color: var(--color-retro-primary);
		font-family: 'VT323', monospace;
		font-size: 12px;
		text-transform: uppercase;
		cursor: pointer;
		text-align: center;
		transition:
			background 0.15s,
			color 0.15s;
	}

	.node-play-btn:hover:not(:disabled) {
		background: var(--color-retro-primary);
		color: var(--color-retro-bg);
	}

	.node-play-btn.playing {
		border-color: #ff4444;
		color: #ff4444;
	}

	.node-play-btn.playing:hover:not(:disabled) {
		background: #ff4444;
		color: var(--color-retro-bg);
	}

	.node-play-btn:disabled {
		opacity: 0.4;
		cursor: not-allowed;
	}

	.node-error {
		margin-top: 2px;
		font-size: 9px;
		color: #ff4444;
		text-align: center;
		word-break: break-all;
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
		color: var(--color-retro-dim);
	}
</style>
