<script lang="ts">
	import { createQuery, createMutation, useQueryClient } from '@tanstack/svelte-query';
	import { guildStore } from '$lib/stores/guild.svelte';
	import { api } from '$lib/apiClient';
	import type {
		MusicControlResponse,
		MusicAddResponse,
		MusicStatusResponse,
		MusicControlRequestActionEnum,
		MusicAddRequest,
		MusicAddRequestTypeEnum
	} from '$lib/api/models';

	const queryClient = useQueryClient();

	let newMusicLink = $state('');
	let newLayerLink = $state('');

	const guildId = $derived(guildStore.current?.id);

	const musicQuery = createQuery(() => ({
		queryKey: ['music', guildId],
		queryFn: async () => {
			if (!guildId) throw new Error('No guild selected');
			return await api.getMusicStatus({
				guildId: guildId
			});
		},
		enabled: !!guildId,
		refetchInterval: 5000
	}));

	const controlMutation = createMutation<
		MusicControlResponse,
		Error,
		{
			action: MusicControlRequestActionEnum;
			mode?: string;
			layer_id?: string;
			volume?: number;
		}
	>(() => ({
		mutationFn: async ({ action, mode, layer_id, volume }) => {
			if (!guildId) throw new Error('No guild selected');
			return await api.postMusicControl({
				musicControlRequest: {
					guildId: guildId,
					action,
					mode: mode ?? null,
					layerId: layer_id ?? null,
					volume: volume ?? null
				}
			});
		},
		onSuccess: () => {
			queryClient.invalidateQueries({ queryKey: ['music', guildId] });
		},
		onError: (error: Error) => {
			console.error('Control failed', error);
		}
	}));

	const addMusicMutation = createMutation<
		MusicAddResponse,
		Error,
		{ link: string; type?: MusicAddRequestTypeEnum }
	>(() => ({
		mutationFn: async ({ link, type }) => {
			if (!guildId) throw new Error('No guild selected');
			return await api.postMusicAdd({
				musicAddRequest: {
					guildId: guildId,
					link,
					type: type ?? 'queue'
				}
			});
		},
		onSuccess: (_, variables) => {
			if (variables.type === 'layer') {
				newLayerLink = '';
			} else {
				newMusicLink = '';
			}
			queryClient.invalidateQueries({ queryKey: ['music', guildId] });
		},
		onError: (error: Error) => {
			console.error('Add music failed', error);
		}
	}));

	const musicData = $derived(musicQuery.data);
	const connected = $derived(!!musicData);

	function handleAddMusic(e: SubmitEvent) {
		e.preventDefault();
		if (newMusicLink.trim()) {
			addMusicMutation.mutate({
				link: newMusicLink.trim(),
				type: 'queue' as MusicAddRequestTypeEnum
			});
		}
	}

	function handleAddLayer(e: SubmitEvent) {
		e.preventDefault();
		if (newLayerLink.trim()) {
			addMusicMutation.mutate({
				link: newLayerLink.trim(),
				type: 'layer' as MusicAddRequestTypeEnum
			});
		}
	}
</script>

<div class="mx-auto max-w-4xl space-y-8">
	<div class="mb-6 flex items-end justify-between border-b-2 border-retro-primary pb-2">
		<h1 class="text-4xl font-bold">AUDIO // CONTROL</h1>
		<div class="mb-1 text-sm text-retro-dim">
			STATUS: {connected ? 'LINKED' : 'OFFLINE'}
		</div>
	</div>

	{#if !guildId}
		<div class="crt-flicker py-8 text-center text-xl text-retro-dim">
			SELECT A GUILD TO ACCESS AUDIO CONTROLS
		</div>
	{:else if musicQuery.isLoading}
		<div class="crt-flicker">LOADING DATA STREAMS...</div>
	{:else if musicQuery.isError}
		<div class="py-4 text-center text-retro-dim">NO ACTIVE AUDIO SESSION</div>
	{:else}
		<!-- Add Music Form -->
		<form onsubmit={handleAddMusic} class="retro-border flex gap-4 bg-black/30 p-4">
			<input
				type="text"
				bind:value={newMusicLink}
				placeholder="ENTER YOUTUBE LINK..."
				class="flex-1 border border-retro-primary bg-retro-bg px-4 py-2 text-retro-primary placeholder:text-retro-dim"
			/>
			<button
				type="submit"
				disabled={addMusicMutation.isPending || !newMusicLink.trim()}
				class="border-2 border-retro-primary px-6 py-2 font-bold transition-colors hover:bg-retro-primary hover:text-retro-bg disabled:opacity-50"
			>
				{addMusicMutation.isPending ? 'ADDING...' : '[ ADD ]'}
			</button>
		</form>

		<!-- Now Playing -->
		<div class="retro-border relative overflow-hidden bg-black/30 p-6">
			<h2 class="mb-2 text-xl text-retro-dim">NOW PLAYING sequence...</h2>

			{#if musicData?.currentMusic}
				<div class="retro-shadow mb-4 truncate text-3xl font-bold">
					{musicData.currentMusic.title}
				</div>

				<div class="mb-4">
					<div class="mb-1 flex justify-between text-xs">
						<span>{musicData.progress}s</span>
						<span>{musicData.currentMusic.duration}</span>
					</div>
					<div class="h-6 w-full border border-retro-primary bg-retro-off p-1">
						<div class="h-full w-full animate-pulse bg-retro-primary opacity-50"></div>
					</div>
				</div>
			{:else}
				<div class="text-2xl text-retro-dim italic">NO AUDIO SIGNAL DETECTED</div>
			{/if}

			<!-- Controls -->
			<div class="mt-6 flex flex-wrap justify-center gap-4">
				{#if musicData?.isPaused}
					<button
						onclick={() => controlMutation.mutate({ action: 'resume' })}
						disabled={controlMutation.isPending}
						class="border-2 border-retro-primary px-6 py-2 font-bold transition-colors hover:bg-retro-primary hover:text-retro-bg disabled:opacity-50"
					>
						[ RESUME ]
					</button>
				{:else}
					<button
						onclick={() => controlMutation.mutate({ action: 'pause' })}
						disabled={controlMutation.isPending}
						class="border-2 border-retro-primary px-6 py-2 font-bold transition-colors hover:bg-retro-primary hover:text-retro-bg disabled:opacity-50"
					>
						[ PAUSE ]
					</button>
				{/if}
				<button
					onclick={() => controlMutation.mutate({ action: 'stop' })}
					disabled={controlMutation.isPending}
					class="border-2 border-retro-primary px-6 py-2 font-bold transition-colors hover:bg-retro-primary hover:text-retro-bg disabled:opacity-50"
				>
					[ STOP ]
				</button>
				<button
					onclick={() => controlMutation.mutate({ action: 'skip' })}
					disabled={controlMutation.isPending}
					class="border-2 border-retro-primary px-6 py-2 font-bold transition-colors hover:bg-retro-primary hover:text-retro-bg disabled:opacity-50"
				>
					[ SKIP ]
				</button>
				<button
					onclick={() => {
						const modes: string[] = ['off', 'track', 'queue'];
						const currentIdx = modes.indexOf(musicData?.loopMode || 'off');
						const nextMode = modes[(currentIdx + 1) % modes.length];
						controlMutation.mutate({ action: 'loop', mode: nextMode });
					}}
					disabled={controlMutation.isPending}
					class="border-2 border-retro-primary px-6 py-2 font-bold transition-colors hover:bg-retro-primary hover:text-retro-bg disabled:opacity-50"
				>
					[ LOOP: {musicData?.loopMode?.toString().toUpperCase() || 'OFF'} ]
				</button>
			</div>

			<!-- Volume Control -->
			<div class="mt-6 flex items-center gap-4 border-t border-retro-dim/30 pt-4">
				<span class="text-sm font-bold text-retro-dim">MASTER VOL</span>
				<input
					type="range"
					min="0"
					max="2"
					step="0.05"
					value={musicData?.volume ?? 0.5}
					onchange={(e: Event) =>
						controlMutation.mutate({
							action: 'set_volume',
							volume: parseFloat((e.target as HTMLInputElement).value)
						})}
					class="h-2 flex-1 cursor-pointer appearance-none bg-retro-dim/30 accent-retro-primary"
				/>
				<span class="w-12 text-right text-sm text-retro-dim">
					{Math.round((musicData?.volume ?? 0.5) * 100)}%
				</span>
			</div>
		</div>

		<!-- Background Layers -->
		<div class="retro-border bg-black/30 p-6">
			<h2 class="mb-4 flex items-center justify-between border-b border-retro-dim pb-2 text-xl">
				<span>BACKGROUND LAYERS</span>
				<button
					onclick={() => controlMutation.mutate({ action: 'clean_layers' })}
					class="text-sm text-red-500 hover:text-red-400 disabled:opacity-50"
					disabled={!musicData?.layers?.length || controlMutation.isPending}
				>
					[ CLEAR ALL ]
				</button>
			</h2>

			<!-- Add Layer Form -->
			<form onsubmit={handleAddLayer} class="mb-4 flex gap-4">
				<input
					type="text"
					bind:value={newLayerLink}
					placeholder="ADD LAYER URL..."
					class="flex-1 border border-retro-primary bg-retro-bg px-4 py-2 text-retro-primary placeholder:text-retro-dim"
				/>
				<button
					type="submit"
					disabled={addMusicMutation.isPending || !newLayerLink.trim()}
					class="border-2 border-retro-primary px-4 py-2 font-bold transition-colors hover:bg-retro-primary hover:text-retro-bg disabled:opacity-50"
				>
					{addMusicMutation.isPending ? '...' : '[ + ]'}
				</button>
			</form>

			{#if musicData?.layers && musicData.layers.length > 0}
				<ul class="space-y-2">
					{#each musicData.layers as layer (layer.id)}
						<li class="flex flex-col gap-2 border-b border-retro-dim/20 pb-2 last:border-0">
							<div class="flex items-center gap-4">
								<span class="flex-1 truncate">{layer.title}</span>
								<button
									onclick={() =>
										controlMutation.mutate({ action: 'remove_layer', layer_id: layer.id })}
									disabled={controlMutation.isPending}
									class="text-retro-dim hover:text-retro-primary"
								>
									[ REMOVE ]
								</button>
							</div>
							<div class="flex items-center gap-3 px-2">
								<span class="text-xs text-retro-dim">VOL</span>
								<input
									type="range"
									min="0"
									max="2"
									step="0.05"
									value={layer.volume ?? 0.3}
									onchange={(e: Event) =>
										controlMutation.mutate({
											action: 'set_layer_volume',
											layer_id: layer.id,
											volume: parseFloat((e.target as HTMLInputElement).value)
										})}
									class="h-1 flex-1 cursor-pointer appearance-none bg-retro-dim/30 accent-retro-primary"
								/>
								<span class="w-8 text-right text-xs text-retro-dim">
									{Math.round((layer.volume ?? 0.3) * 100)}%
								</span>
							</div>
						</li>
					{/each}
				</ul>
			{:else}
				<div class="py-4 text-center text-retro-dim">NO ACTIVE LAYERS</div>
			{/if}
		</div>

		<!-- Queue -->
		<div class="retro-border bg-black/30 p-6">
			<h2 class="mb-4 border-b border-retro-dim pb-2 text-xl">QUEUE SEQUENCE</h2>
			{#if musicData?.queue && musicData.queue.length > 0}
				<ul class="space-y-2">
					{#each musicData.queue as track, i (track.title + i)}
						<li class="flex items-center gap-4">
							<span class="w-6 text-retro-dim">{i + 1}.</span>
							<span class="flex-1 truncate">{track.title}</span>
							<span class="text-sm text-retro-dim">{track.duration}</span>
						</li>
					{/each}
				</ul>
			{:else}
				<div class="py-4 text-center text-retro-dim">QUEUE BUFFER EMPTY</div>
			{/if}
		</div>
	{/if}
</div>
