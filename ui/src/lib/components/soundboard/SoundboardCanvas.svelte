<script lang="ts">
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
	import '$lib/styles/svelteflow-theme.css';

	interface Props {
		nodes: Node[];
		edges: Edge[];
		nodeTypes: NodeTypes;
		onNodeDragStop: (targetNode: Node) => void;
		onConnect: (connection: { source: string; target: string }) => void;
		onDelete: (deleted: { nodes: Node[]; edges: Edge[] }) => void;
	}

	let { nodes = $bindable(), edges = $bindable(), nodeTypes, onNodeDragStop, onConnect, onDelete }: Props =
		$props();

	const NODE_COLORS: Record<string, string> = {
		'sound-source': '#ffb800',
		playlist: '#00b8ff',
		mixer: '#00ff88',
		output: '#ff4444'
	};
</script>

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
				if (targetNode) onNodeDragStop(targetNode);
			}}
			onconnect={(connection) => onConnect(connection)}
			deleteKey="Delete"
			ondelete={({ nodes: deletedNodes, edges: deletedEdges }) => {
				onDelete({ nodes: deletedNodes, edges: deletedEdges });
			}}
		>
			<Background bgColor="#1a150e" />
			<Controls />
			<MiniMap
				nodeColor={(node: Node) => NODE_COLORS[node.type || ''] || '#ffb800'}
				maskColor="rgba(26, 21, 14, 0.8)"
			/>
		</SvelteFlow>
	</div>
</SvelteFlowProvider>
