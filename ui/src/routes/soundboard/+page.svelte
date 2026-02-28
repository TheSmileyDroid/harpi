<script lang="ts">
	import { untrack } from 'svelte';
	import { createQuery, createMutation } from '@tanstack/svelte-query';
	import { guildStore } from '$lib/stores/guild.svelte';
	import type { Node, Edge, NodeTypes } from '@xyflow/svelte';
	import { soundboardStore, generateNodeId, generateEdgeId } from '$lib/stores/soundboard.svelte';
	import type { SoundboardNode, SoundboardEdge } from '$lib/types/soundboard';
	import SoundSourceNode from '$lib/components/soundboard/SoundSourceNode.svelte';
	import PlaylistNode from '$lib/components/soundboard/PlaylistNode.svelte';
	import MixerNode from '$lib/components/soundboard/MixerNode.svelte';
	import OutputNode from '$lib/components/soundboard/OutputNode.svelte';
	import SoundboardSidebar from '$lib/components/soundboard/SoundboardSidebar.svelte';
	import SoundboardCanvas from '$lib/components/soundboard/SoundboardCanvas.svelte';

	const guildId = $derived(guildStore.current?.id);

	const nodeTypes: NodeTypes = {
		'sound-source': SoundSourceNode as NodeTypes[string],
		playlist: PlaylistNode as NodeTypes[string],
		mixer: MixerNode as NodeTypes[string],
		output: OutputNode as NodeTypes[string]
	};

	// --- Sidebar state ---

	let sourceUrl = $state('');
	let sourceLoading = $state(false);
	let sourceError = $state('');
	let playlistUrl = $state('');
	let playlistLoading = $state(false);
	let playlistError = $state('');

	let saveError = $state('');

	// Dirty guard: timestamp of last local graph change.
	let lastLocalChange = $state(0);
	const DIRTY_GUARD_MS = 6000;

	// --- Flow data mapping ---

	function enrichNodeData(n: SoundboardNode, storeNodes: SoundboardNode[]): Record<string, unknown> {
		const extra: Record<string, unknown> = {};
		if (guildId) extra.guildId = guildId;

		const active = soundboardStore.activeNodes.find((a) => a.nodeId === n.id);
		if (active) {
			extra.playing = active.playing;
			extra.progress = active.progress;
			extra.volume = active.volume;
		}

		if (n.type === 'mixer') {
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
			extra.inputs = inputs;
			extra.active = inputs.some(
				(i) => soundboardStore.activeNodes.find((a) => a.nodeId === i.nodeId)?.playing
			);
		}

		if (n.type === 'output') {
			extra.connected = soundboardStore.connected;
			extra.channelName = soundboardStore.channelName || '---';
			extra.activeCount = soundboardStore.activeNodes.length;
		}

		return extra;
	}

	function storeNodesToFlow(storeNodes: SoundboardNode[]): Node[] {
		return storeNodes.map((n): Node => ({
			id: n.id,
			type: n.type,
			position: n.position,
			data: { ...n.data, ...enrichNodeData(n, storeNodes) },
			draggable: n.type !== 'output',
			deletable: n.type !== 'output',
			selectable: true
		}));
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

	// --- Reactive flow state ---

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
		},
		onError: (error: Error) => {
			saveError = error.message || 'Failed to save graph';
			console.error('Graph save failed:', error);
		},
		onSuccess: () => {
			saveError = '';
		}
	}));

	// --- Debounced save ---

	let saveTimeout: ReturnType<typeof setTimeout>;
	function debouncedSave() {
		lastLocalChange = Date.now();
		clearTimeout(saveTimeout);
		saveTimeout = setTimeout(() => {
			updateGraphMutation.mutate();
		}, 500);
	}

	// --- Sidebar actions ---

	async function fetchMetadata(url: string): Promise<{ title: string; duration: number; thumbnail?: string }> {
		const res = await fetch('/api/soundboard/node/metadata', {
			method: 'POST',
			headers: { 'Content-Type': 'application/json' },
			body: JSON.stringify({ url })
		});
		if (!res.ok) {
			const err = await res.json();
			throw new Error(err.error || 'Failed to fetch metadata');
		}
		return res.json();
	}

	async function addSoundSource() {
		if (!sourceUrl.trim() || !guildId) return;
		sourceLoading = true;
		sourceError = '';

		try {
			const meta = await fetchMetadata(sourceUrl.trim());
			const newNode: SoundboardNode = {
				id: generateNodeId('sound-source'),
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
			const meta = await fetchMetadata(playlistUrl.trim());
			const existingPlaylist = soundboardStore.nodes.find((n) => n.type === 'playlist');

			if (existingPlaylist) {
				const items = (existingPlaylist.data.items || []) as Array<{
					title: string;
					duration: number;
					url: string;
				}>;
				items.push({ title: meta.title, duration: meta.duration, url: playlistUrl.trim() });
				soundboardStore.updateNode(existingPlaylist.id, { items });
			} else {
				const newNode: SoundboardNode = {
					id: generateNodeId('playlist'),
					type: 'playlist',
					data: {
						volume: 100,
						loop: true,
						items: [{ title: meta.title, duration: meta.duration, url: playlistUrl.trim() }],
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
		const newNode: SoundboardNode = {
			id: generateNodeId('mixer'),
			type: 'mixer',
			data: { volume: 100, label: 'MIXER' },
			position: { x: 350 + Math.random() * 100, y: 50 + Math.random() * 300 }
		};
		soundboardStore.addNode(newNode);
		debouncedSave();
	}

	function removeNode(nodeId: string) {
		soundboardStore.removeNode(nodeId);
		debouncedSave();
	}

	// --- Canvas handlers ---

	function handleConnect(params: { source: string; target: string }) {
		const newEdge: SoundboardEdge = {
			id: generateEdgeId(),
			source: params.source,
			target: params.target
		};
		soundboardStore.addEdge(newEdge);
		debouncedSave();
	}

	function handleNodeDragStop(targetNode: Node) {
		const updatedNodes = soundboardStore.nodes.map((n) =>
			n.id === targetNode.id ? { ...n, position: targetNode.position } : n
		);
		soundboardStore.setNodes(updatedNodes);
		debouncedSave();
	}

	function handleDelete({ nodes: deletedNodes, edges: deletedEdges }: { nodes: Node[]; edges: Edge[] }) {
		for (const node of deletedNodes) {
			if (node.id !== 'output-main') {
				soundboardStore.removeNode(node.id);
			}
		}
		for (const edge of deletedEdges) {
			soundboardStore.removeEdge(edge.id);
		}
		debouncedSave();
	}
</script>

<div class="flex h-[calc(100vh-180px)]">
	<SoundboardSidebar
		{sourceUrl}
		{sourceLoading}
		{sourceError}
		{playlistUrl}
		{playlistLoading}
		{playlistError}
		onAddSource={addSoundSource}
		onAddPlaylist={addPlaylistItem}
		onAddMixer={addMixer}
		onRemoveNode={removeNode}
		onSourceUrlChange={(v) => (sourceUrl = v)}
		onPlaylistUrlChange={(v) => (playlistUrl = v)}
	/>

	<div class="flex-1">
		{#if !guildId}
			<div class="flex h-full items-center justify-center text-retro-dim">
				SELECT A GUILD TO USE SOUNDBOARD
			</div>
		{:else}
			{#if saveError}
				<div class="border border-red-500 bg-red-500/10 px-4 py-2 text-sm text-red-400">
					SAVE FAILED: {saveError}
					<button onclick={() => (saveError = '')} class="ml-2 text-red-300 hover:text-red-100">
						[ DISMISS ]
					</button>
				</div>
			{/if}
			<SoundboardCanvas
				bind:nodes
				bind:edges
				{nodeTypes}
				onNodeDragStop={handleNodeDragStop}
				onConnect={handleConnect}
				onDelete={handleDelete}
			/>
		{/if}
	</div>
</div>
