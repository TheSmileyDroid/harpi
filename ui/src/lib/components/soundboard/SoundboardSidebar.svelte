<script lang="ts">
	import { soundboardStore } from '$lib/stores/soundboard.svelte';
	import UrlInputForm from './UrlInputForm.svelte';

	interface Props {
		sourceUrl: string;
		sourceLoading: boolean;
		sourceError: string;
		playlistUrl: string;
		playlistLoading: boolean;
		playlistError: string;
		onAddSource: () => void;
		onAddPlaylist: () => void;
		onAddMixer: () => void;
		onRemoveNode: (nodeId: string) => void;
		onSourceUrlChange: (value: string) => void;
		onPlaylistUrlChange: (value: string) => void;
	}

	let {
		sourceUrl,
		sourceLoading,
		sourceError,
		playlistUrl,
		playlistLoading,
		playlistError,
		onAddSource,
		onAddPlaylist,
		onAddMixer,
		onRemoveNode,
		onSourceUrlChange,
		onPlaylistUrlChange
	}: Props = $props();
</script>

<div class="flex w-72 flex-col gap-3 border-r border-retro-dim bg-retro-bg p-4">
	<h2 class="border-b border-retro-dim pb-2 text-xl font-bold text-retro-primary">SOUNDBOARD</h2>

	<!-- Status -->
	<div class="text-sm">
		<div class="text-retro-dim">STATUS:</div>
		<div class={soundboardStore.connected ? 'text-green-500' : 'text-red-500'}>
			{soundboardStore.connected ? 'CONNECTION ESTABLISHED' : 'NO SIGNAL'}
		</div>
		{#if soundboardStore.channelName}
			<div class="mt-1 text-retro-dim">CH: {soundboardStore.channelName}</div>
		{/if}
	</div>

	<!-- Add Sound Source -->
	<UrlInputForm
		label="ADD SOUND SOURCE"
		value={sourceUrl}
		loading={sourceLoading}
		error={sourceError}
		onsubmit={onAddSource}
		oninput={onSourceUrlChange}
	/>

	<!-- Add Playlist Item -->
	<UrlInputForm
		label="ADD TO PLAYLIST"
		value={playlistUrl}
		loading={playlistLoading}
		error={playlistError}
		onsubmit={onAddPlaylist}
		oninput={onPlaylistUrlChange}
	/>

	<!-- Add Mixer -->
	<button
		onclick={onAddMixer}
		class="border border-retro-primary px-3 py-2 text-sm text-retro-primary transition-colors hover:bg-retro-primary hover:text-retro-bg"
	>
		[ + MIXER ]
	</button>

	<!-- Node list -->
	<div class="flex-1 overflow-y-auto">
		<h3 class="mb-2 border-b border-retro-dim pb-1 text-xs text-retro-dim">
			NODES ({soundboardStore.nodes.length})
		</h3>
		{#each soundboardStore.nodes.filter((n) => n.type !== 'output') as node (node.id)}
			<div
				class="mb-1 flex items-center justify-between border border-retro-off bg-black/20 px-2 py-1"
			>
				<div class="min-w-0 flex-1">
					<span class="text-xs font-bold text-retro-primary">
						{node.data.title || node.type}
					</span>
				</div>
				<button
					onclick={() => onRemoveNode(node.id)}
					class="ml-1 flex-shrink-0 px-1 text-xs text-red-500 hover:text-red-400"
				>
					[X]
				</button>
			</div>
		{/each}
	</div>
</div>
