<script lang="ts">
	import { untrack } from 'svelte';
	import { createQuery, createMutation } from '@tanstack/svelte-query';
	import { guildStore } from '$lib/stores/guild.svelte';
	import {
		SvelteFlowProvider,
		SvelteFlow,
		Background,
		Controls,
		MiniMap,
		type Node,
		type Edge,
		type NodeTypes
	} from '@xyflow/svelte';
	import '@xyflow/svelte/dist/style.css';
	import { soundboardStore, generateNodeId, generateEdgeId } from '$lib/stores/soundboard.svelte';
	import type { SoundboardNode, SoundboardEdge } from '$lib/types/soundboard';
	import SoundSourceNode from '$lib/components/soundboard/SoundSourceNode.svelte';
	import PlaylistNode from '$lib/components/soundboard/PlaylistNode.svelte';
	import MixerNode from '$lib/components/soundboard/MixerNode.svelte';
	import OutputNode from '$lib/components/soundboard/OutputNode.svelte';

	const guildId = $derived(guildStore.current?.id);

	// Custom node types
	const nodeTypes: NodeTypes = {
		'sound-source': SoundSourceNode as NodeTypes[string],
		playlist: PlaylistNode as NodeTypes[string],
		mixer: MixerNode as NodeTypes[string],
		output: OutputNode as NodeTypes[string]
	};

	// Sidebar state
	let sourceUrl = $state('');
	let sourceLoading = $state(false);
	let sourceError = $state('');
	let playlistUrl = $state('');
	let playlistLoading = $state(false);
	let playlistError = $state('');

	// Dirty guard: timestamp of last local graph change.
	// When set, the graphQuery effect skips overwriting local state
	// until enough time has passed for the save to complete.
	let lastLocalChange = $state(0);
	const DIRTY_GUARD_MS = 6000;

	// Merge active node status into flow nodes
	function storeNodesToFlow(storeNodes: SoundboardNode[]): Node[] {
		return storeNodes.map((n): Node => {
			const active = soundboardStore.activeNodes.find((a) => a.nodeId === n.id);
			const extraData: Record<string, unknown> = {};

			// Inject guildId so nodes can call backend endpoints
			if (guildId) {
				extraData.guildId = guildId;
			}

			if (active) {
				extraData.playing = active.playing;
				extraData.progress = active.progress;
				extraData.volume = active.volume;
			}

			if (n.type === 'mixer') {
				// Find all edges targeting this mixer and build inputs list
				const incomingEdges = soundboardStore.edges.filter((e) => e.target === n.id);
				const inputs = incomingEdges.map((e) => {
					const sourceNode = storeNodes.find((sn) => sn.id === e.source);
					const sourceActive = soundboardStore.activeNodes.find((a) => a.nodeId === e.source);
					return {
						nodeId: e.source,
						label: (sourceNode?.data?.title as string) || sourceNode?.type || '???',
						volume: (sourceActive?.volume as number) ?? (sourceNode?.data?.volume as number) ?? 0
					};
				});
				extraData.inputs = inputs;
				extraData.active = inputs.some(
					(i) => soundboardStore.activeNodes.find((a) => a.nodeId === i.nodeId)?.playing
				);
			}

			if (n.type === 'output') {
				extraData.connected = soundboardStore.connected;
				extraData.channelName = soundboardStore.channelName || '---';
				extraData.activeCount = soundboardStore.activeNodes.length;
			}

			return {
				id: n.id,
				type: n.type,
				position: n.position,
				data: { ...n.data, ...extraData },
				draggable: n.type !== 'output',
				deletable: n.type !== 'output',
				selectable: true
			};
		});
	}

	function storeEdgesToFlow(storeEdges: SoundboardEdge[], existingEdges: Edge[]): Edge[] {
		return storeEdges.map((e): Edge => {
			const existing = existingEdges.find((ex) => ex.id === e.id);
			return {
				id: e.id,
				source: e.source,
				target: e.target,
				type: 'smoothstep',
				animated: true,
				selectable: true,
				deletable: true,
				selected: existing?.selected ?? false,
				style: 'stroke: var(--color-retro-dim); stroke-width: 2px;'
			};
		});
	}

	// Reactive flow data - $state + $effect needed for SvelteFlow bind:nodes/bind:edges
	// eslint-disable-next-line svelte/prefer-writable-derived
	let nodes = $state<Node[]>(storeNodesToFlow(soundboardStore.nodes));
	// eslint-disable-next-line svelte/prefer-writable-derived
	let edges = $state<Edge[]>(storeEdgesToFlow(soundboardStore.edges, []));

	$effect(() => {
		nodes = storeNodesToFlow(soundboardStore.nodes);
	});

	$effect(() => {
		edges = storeEdgesToFlow(
			soundboardStore.edges,
			untrack(() => edges)
		);
	});

	// Ensure output node exists
	$effect(() => {
		if (guildId && !soundboardStore.nodes.find((n) => n.type === 'output')) {
			const outputNode: SoundboardNode = {
				id: 'output-main',
				type: 'output',
				data: { volume: 100 },
				position: { x: 600, y: 200 }
			};
			soundboardStore.addNode(outputNode);
			debouncedSave();
		}
	});

	// --- Queries ---

	const statusQuery = createQuery(() => ({
		queryKey: ['soundboard-status', guildId],
		queryFn: async () => {
			if (!guildId) throw new Error('No guild selected');
			const res = await fetch(`/api/soundboard/status/${guildId}`);
			if (!res.ok) throw new Error('Failed to fetch status');
			return res.json();
		},
		enabled: !!guildId,
		refetchInterval: 1000
	}));

	const graphQuery = createQuery(() => ({
		queryKey: ['soundboard-graph', guildId],
		queryFn: async () => {
			if (!guildId) throw new Error('No guild selected');
			const res = await fetch(`/api/soundboard/graph/${guildId}`);
			if (!res.ok) throw new Error('Failed to fetch graph');
			return res.json();
		},
		enabled: !!guildId,
		refetchInterval: 5000
	}));

	$effect(() => {
		if (statusQuery.data) {
			soundboardStore.setStatus(statusQuery.data as Record<string, unknown>);
		}
	});

	$effect(() => {
		if (graphQuery.data && graphQuery.data.nodes) {
			// Skip overwriting local state if a local change happened recently
			if (lastLocalChange && Date.now() - lastLocalChange < DIRTY_GUARD_MS) {
				return;
			}
			// eslint-disable-next-line @typescript-eslint/no-explicit-any
			const graphNodes = graphQuery.data.nodes.map((n: any) => ({
				id: n.id,
				type: n.type,
				data: n.data || {},
				position: n.position
			}));
			// eslint-disable-next-line @typescript-eslint/no-explicit-any
			const graphEdges = graphQuery.data.edges.map((e: any) => ({
				id: e.id,
				source: e.source,
				target: e.target
			}));
			soundboardStore.setNodes(graphNodes);
			soundboardStore.setEdges(graphEdges);
		}
	});

	// --- Mutations ---

	const updateGraphMutation = createMutation(() => ({
		mutationFn: async () => {
			if (!guildId) throw new Error('No guild selected');
			const res = await fetch(`/api/soundboard/graph/${guildId}`, {
				method: 'PUT',
				headers: { 'Content-Type': 'application/json' },
				body: JSON.stringify({
					nodes: soundboardStore.nodes,
					edges: soundboardStore.edges
				})
			});
			if (!res.ok) throw new Error('Failed to save graph');
			return res.json();
		}
	}));

	// --- Sidebar actions ---

	async function addSoundSource() {
		if (!sourceUrl.trim() || !guildId) return;
		sourceLoading = true;
		sourceError = '';

		try {
			const res = await fetch('/api/soundboard/node/metadata', {
				method: 'POST',
				headers: { 'Content-Type': 'application/json' },
				body: JSON.stringify({ url: sourceUrl.trim() })
			});
			if (!res.ok) {
				const err = await res.json();
				throw new Error(err.error || 'Failed to fetch metadata');
			}
			const meta = await res.json();

			const id = generateNodeId('sound-source');
			const newNode: SoundboardNode = {
				id,
				type: 'sound-source',
				data: {
					title: meta.title,
					url: sourceUrl.trim(),
					duration: meta.duration,
					thumbnail: meta.thumbnail,
					volume: 100,
					loop: true
				},
				position: { x: 50 + Math.random() * 200, y: 50 + Math.random() * 300 }
			};
			soundboardStore.addNode(newNode);
			sourceUrl = '';
			debouncedSave();
		} catch (e: unknown) {
			sourceError = e instanceof Error ? e.message : 'Unknown error';
		} finally {
			sourceLoading = false;
		}
	}

	async function addPlaylistItem() {
		if (!playlistUrl.trim() || !guildId) return;
		playlistLoading = true;
		playlistError = '';

		try {
			const res = await fetch('/api/soundboard/node/metadata', {
				method: 'POST',
				headers: { 'Content-Type': 'application/json' },
				body: JSON.stringify({ url: playlistUrl.trim() })
			});
			if (!res.ok) {
				const err = await res.json();
				throw new Error(err.error || 'Failed to fetch metadata');
			}
			const meta = await res.json();

			// Find existing playlist node or create new one
			let playlistNode = soundboardStore.nodes.find((n) => n.type === 'playlist');

			if (playlistNode) {
				const items = (playlistNode.data.items || []) as Array<{
					title: string;
					duration: number;
					url: string;
				}>;
				items.push({
					title: meta.title,
					duration: meta.duration,
					url: playlistUrl.trim()
				});
				soundboardStore.updateNode(playlistNode.id, { items });
			} else {
				const id = generateNodeId('playlist');
				const newNode: SoundboardNode = {
					id,
					type: 'playlist',
					data: {
						volume: 100,
						loop: true,
						items: [
							{
								title: meta.title,
								duration: meta.duration,
								url: playlistUrl.trim()
							}
						],
						currentIndex: -1
					},
					position: { x: 50 + Math.random() * 200, y: 50 + Math.random() * 300 }
				};
				soundboardStore.addNode(newNode);
			}

			playlistUrl = '';
			debouncedSave();
		} catch (e: unknown) {
			playlistError = e instanceof Error ? e.message : 'Unknown error';
		} finally {
			playlistLoading = false;
		}
	}

	function addMixer() {
		const id = generateNodeId('mixer');
		const newNode: SoundboardNode = {
			id,
			type: 'mixer',
			data: { volume: 100, label: 'MIXER' },
			position: { x: 350 + Math.random() * 100, y: 50 + Math.random() * 300 }
		};
		soundboardStore.addNode(newNode);
		debouncedSave();
	}

	// --- Graph interactions ---

	function onConnect(params: { source: string; target: string }) {
		const newEdge: SoundboardEdge = {
			id: generateEdgeId(),
			source: params.source,
			target: params.target
		};
		soundboardStore.addEdge(newEdge);
		debouncedSave();
	}

	let saveTimeout: ReturnType<typeof setTimeout>;
	function debouncedSave() {
		lastLocalChange = Date.now();
		clearTimeout(saveTimeout);
		saveTimeout = setTimeout(() => {
			updateGraphMutation.mutate();
		}, 500);
	}

	function handleKeydown(e: KeyboardEvent, action: () => void) {
		if (e.key === 'Enter') action();
	}
</script>

<div class="flex h-[calc(100vh-180px)]">
	<!-- Sidebar -->
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
		<div class="border border-retro-off bg-black/30 p-3">
			<div class="mb-2 text-xs text-retro-dim">ADD SOUND SOURCE</div>
			<div class="flex gap-1">
				<input
					type="text"
					bind:value={sourceUrl}
					onkeydown={(e: KeyboardEvent) => handleKeydown(e, addSoundSource)}
					placeholder="youtube url..."
					disabled={sourceLoading}
					class="flex-1 border border-retro-dim bg-retro-bg px-2 py-1 text-xs text-retro-primary placeholder:text-retro-off disabled:opacity-50"
				/>
				<button
					onclick={addSoundSource}
					disabled={sourceLoading || !sourceUrl.trim()}
					class="border border-retro-primary px-2 py-1 text-xs text-retro-primary transition-colors hover:bg-retro-primary hover:text-retro-bg disabled:opacity-50"
				>
					{sourceLoading ? '...' : '[ ADD ]'}
				</button>
			</div>
			{#if sourceError}
				<div class="mt-1 text-xs text-red-500">{sourceError}</div>
			{/if}
		</div>

		<!-- Add Playlist Item -->
		<div class="border border-retro-off bg-black/30 p-3">
			<div class="mb-2 text-xs text-retro-dim">ADD TO PLAYLIST</div>
			<div class="flex gap-1">
				<input
					type="text"
					bind:value={playlistUrl}
					onkeydown={(e: KeyboardEvent) => handleKeydown(e, addPlaylistItem)}
					placeholder="youtube url..."
					disabled={playlistLoading}
					class="flex-1 border border-retro-dim bg-retro-bg px-2 py-1 text-xs text-retro-primary placeholder:text-retro-off disabled:opacity-50"
				/>
				<button
					onclick={addPlaylistItem}
					disabled={playlistLoading || !playlistUrl.trim()}
					class="border border-retro-primary px-2 py-1 text-xs text-retro-primary transition-colors hover:bg-retro-primary hover:text-retro-bg disabled:opacity-50"
				>
					{playlistLoading ? '...' : '[ ADD ]'}
				</button>
			</div>
			{#if playlistError}
				<div class="mt-1 text-xs text-red-500">{playlistError}</div>
			{/if}
		</div>

		<!-- Add Mixer -->
		<button
			onclick={addMixer}
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
						onclick={() => {
							soundboardStore.removeNode(node.id);
							debouncedSave();
						}}
						class="ml-1 flex-shrink-0 px-1 text-xs text-red-500 hover:text-red-400"
					>
						[X]
					</button>
				</div>
			{/each}
		</div>
	</div>

	<!-- Graph Canvas -->
	<div class="flex-1">
		{#if !guildId}
			<div class="flex h-full items-center justify-center text-retro-dim">
				SELECT A GUILD TO USE SOUNDBOARD
			</div>
		{:else}
			<SvelteFlowProvider>
				<div class="h-full w-full">
					<SvelteFlow
						bind:nodes
						bind:edges
						{nodeTypes}
						minZoom={0.1}
						maxZoom={2}
						fitView
						colorMode="dark"
						onnodedragstop={({ targetNode }) => {
							if (!targetNode) return;
							const updatedNodes = soundboardStore.nodes.map((n) =>
								n.id === targetNode.id ? { ...n, position: targetNode.position } : n
							);
							soundboardStore.setNodes(updatedNodes);
							debouncedSave();
						}}
						onconnect={(connection) => onConnect(connection)}
						deleteKey="Delete"
						ondelete={({ nodes: deletedNodes, edges: deletedEdges }) => {
							for (const node of deletedNodes) {
								if (node.id !== 'output-main') {
									soundboardStore.removeNode(node.id);
								}
							}
							for (const edge of deletedEdges) {
								soundboardStore.removeEdge(edge.id);
							}
							debouncedSave();
						}}
					>
						<Background bgColor="#1a150e" />
						<Controls />
						<MiniMap
							nodeColor={(node: Node) => {
								const colors: Record<string, string> = {
									'sound-source': '#ffb800',
									playlist: '#00b8ff',
									mixer: '#00ff88',
									output: '#ff4444'
								};
								return colors[node.type || ''] || '#ffb800';
							}}
							maskColor="rgba(26, 21, 14, 0.8)"
						/>
					</SvelteFlow>
				</div>
			</SvelteFlowProvider>
		{/if}
	</div>
</div>

<style>
	:global(.svelte-flow) {
		--xy-background-color: #1a150e;
		--xy-node-border-radius: 0;
		--xy-handle-background-color: var(--color-retro-primary);
		--xy-handle-border-color: var(--color-retro-dim);
		--xy-edge-stroke: var(--color-retro-dim);
		--xy-edge-stroke-selected: var(--color-retro-primary);
		--xy-minimap-background-color: #1a150e;
		--xy-controls-button-background-color: #1a150e;
		--xy-controls-button-color: var(--color-retro-primary);
		--xy-controls-button-border-color: var(--color-retro-dim);
		--xy-attribution-background-color: transparent;
	}

	:global(.svelte-flow .svelte-flow__node) {
		border-radius: 0;
		font-family: 'VT323', monospace;
	}

	:global(.svelte-flow .svelte-flow__handle) {
		width: 8px;
		height: 8px;
		border-radius: 0;
		border: 1px solid var(--color-retro-dim);
		background: var(--color-retro-primary);
	}

	:global(.svelte-flow .svelte-flow__edge-path) {
		stroke: var(--color-retro-dim);
		stroke-width: 2;
	}

	:global(.svelte-flow .svelte-flow__edge.selected .svelte-flow__edge-path) {
		stroke: var(--color-retro-primary);
	}

	:global(.svelte-flow .svelte-flow__controls) {
		border: 1px solid var(--color-retro-dim);
		border-radius: 0;
		box-shadow: 0 0 6px rgba(255, 184, 0, 0.1);
	}

	:global(.svelte-flow .svelte-flow__controls button) {
		background: #1a150e;
		color: var(--color-retro-primary);
		border-color: var(--color-retro-dim);
		border-radius: 0;
	}

	:global(.svelte-flow .svelte-flow__controls button:hover) {
		background: var(--color-retro-off);
	}

	:global(.svelte-flow .svelte-flow__controls button svg) {
		fill: var(--color-retro-primary);
	}

	:global(.svelte-flow .svelte-flow__minimap) {
		border: 1px solid var(--color-retro-dim);
		border-radius: 0;
		background: #1a150e;
	}

	:global(.svelte-flow .svelte-flow__background pattern line) {
		stroke: var(--color-retro-off) !important;
	}
</style>
