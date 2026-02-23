import type { SoundboardNode, SoundboardEdge, ActiveNodeStatus } from '$lib/types/soundboard';

function createSoundboardStore() {
	let nodes = $state<SoundboardNode[]>([]);
	let edges = $state<SoundboardEdge[]>([]);
	let activeNodes = $state<ActiveNodeStatus[]>([]);
	let connected = $state(false);
	let channelId = $state<number | null>(null);
	let channelName = $state<string | null>(null);
	let isLoading = $state(false);
	let statusPolling = $state(false);
	let graphPolling = $state(false);

	return {
		get nodes() {
			return nodes;
		},
		get edges() {
			return edges;
		},
		get activeNodes() {
			return activeNodes;
		},
		get connected() {
			return connected;
		},
		get channelId() {
			return channelId;
		},
		get channelName() {
			return channelName;
		},
		get isLoading() {
			return isLoading;
		},
		get statusPolling() {
			return statusPolling;
		},
		get graphPolling() {
			return graphPolling;
		},

		setNodes(newNodes: SoundboardNode[]) {
			nodes = newNodes;
		},

		setEdges(newEdges: SoundboardEdge[]) {
			edges = newEdges;
		},

		setStatus(raw: Record<string, unknown>) {
			connected = (raw.connected as boolean) ?? false;
			channelId = (raw.channel_id as number | null) ?? null;
			channelName = (raw.channel_name as string | null) ?? null;

			const rawNodes = (raw.active_nodes as Record<string, unknown>[]) || [];
			activeNodes = rawNodes.map(
				(n): ActiveNodeStatus => ({
					nodeId: (n.node_id as string) ?? '',
					layerId: (n.layer_id as string) ?? '',
					playing: (n.playing as boolean) ?? false,
					volume: (n.volume as number) ?? 0,
					progress: (n.progress as number) ?? 0,
					duration: (n.duration as number) ?? 0,
					title: (n.title as string) ?? '',
					url: (n.url as string) ?? ''
				})
			);
		},

		setLoading(loading: boolean) {
			isLoading = loading;
		},

		setStatusPolling(polling: boolean) {
			statusPolling = polling;
		},

		setGraphPolling(polling: boolean) {
			graphPolling = polling;
		},

		addNode(node: SoundboardNode) {
			nodes = [...nodes, node];
		},

		updateNode(nodeId: string, data: Partial<SoundboardNode['data']>) {
			nodes = nodes.map((n) => (n.id === nodeId ? { ...n, data: { ...n.data, ...data } } : n));
		},

		removeNode(nodeId: string) {
			nodes = nodes.filter((n) => n.id !== nodeId);
			edges = edges.filter((e) => e.source !== nodeId && e.target !== nodeId);
		},

		addEdge(edge: SoundboardEdge) {
			edges = [...edges, edge];
		},

		removeEdge(edgeId: string) {
			edges = edges.filter((e) => e.id !== edgeId);
		},

		getActiveNode(nodeId: string): ActiveNodeStatus | undefined {
			return activeNodes.find((n) => n.nodeId === nodeId);
		},

		clear() {
			nodes = [];
			edges = [];
			activeNodes = [];
			connected = false;
			channelId = null;
			channelName = null;
		}
	};
}

export const soundboardStore = createSoundboardStore();

// Helper to generate unique IDs
export function generateNodeId(type: string): string {
	return `${type}-${Date.now()}-${Math.random().toString(36).substr(2, 9)}`;
}

export function generateEdgeId(): string {
	return `edge-${Date.now()}-${Math.random().toString(36).substr(2, 9)}`;
}
