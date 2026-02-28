<script lang="ts">
	import type { SoundboardNode, SoundboardEdge } from '$lib/types/soundboard';
	import type { Component } from 'svelte';
	import SoundSourceNode from './SoundSourceNode.svelte';
	import PlaylistNode from './PlaylistNode.svelte';
	import MixerNode from './MixerNode.svelte';
	import OutputNode from './OutputNode.svelte';

	interface Props {
		nodes: SoundboardNode[];
		edges: SoundboardEdge[];
		nodeTypes: Record<string, Component<any>>;
		onNodeDragStop: (targetNode: SoundboardNode) => void;
		onConnect: (connection: { source: string; target: string }) => void;
		onDelete: (deleted: { nodes: SoundboardNode[]; edges: SoundboardEdge[] }) => void;
	}

	let {
		nodes = $bindable(),
		edges = $bindable(),
		onNodeDragStop,
		onConnect,
		onDelete
	}: Props = $props();

	// --- State ---
	let viewport = $state({ x: 0, y: 0, zoom: 1 });
	let container: HTMLDivElement;
	let isPanning = $state(false);
	let isDraggingNode = $state(false);
	let lastMousePos = { x: 0, y: 0 };
	let draggedNodeId: string | null = $state(null);
	let selectedNodeId: string | null = $state(null);
	let selectedEdgeId: string | null = $state(null);

	// Connection state
	let connectionStart: { nodeId: string; type: 'source' | 'target'; x: number; y: number } | null =
		$state(null);
	let tempConnectionEnd: { x: number; y: number } | null = $state(null);

	// Map of node ID to its DOM element for calculating port positions
	let nodeElements: Record<string, HTMLElement> = {};

	// --- Helpers ---

	function screenToFlow({ x, y }: { x: number; y: number }) {
		if (!container) return { x: 0, y: 0 };
		const rect = container.getBoundingClientRect();
		return {
			x: (x - rect.left - viewport.x) / viewport.zoom,
			y: (y - rect.top - viewport.y) / viewport.zoom
		};
	}

	function getPortPosition(nodeId: string, type: 'source' | 'target') {
		const node = nodes.find((n) => n.id === nodeId);
		const el = nodeElements[nodeId];
		if (!node || !el) return { x: 0, y: 0 };

		// Approximate port positions based on node dimensions
		// Source: Right middle, Target: Left middle
		// Adjust offset slightly to match the visual port position
		if (type === 'source') {
			return {
				x: node.position.x + el.offsetWidth,
				y: node.position.y + el.offsetHeight / 2
			};
		} else {
			return {
				x: node.position.x,
				y: node.position.y + el.offsetHeight / 2
			};
		}
	}

	// --- Event Handlers ---

	function handleWheel(e: WheelEvent) {
		e.preventDefault();
		const zoomFactor = -e.deltaY * 0.001;
		const newZoom = Math.min(Math.max(0.1, viewport.zoom + zoomFactor), 3);

		// Zoom towards cursor
		const rect = container.getBoundingClientRect();
		const cursorX = e.clientX - rect.left;
		const cursorY = e.clientY - rect.top;

		const zoomRatio = newZoom / viewport.zoom;
		
		viewport.x = cursorX - (cursorX - viewport.x) * zoomRatio;
		viewport.y = cursorY - (cursorY - viewport.y) * zoomRatio;
		viewport.zoom = newZoom;
	}

	function handleMouseDown(e: MouseEvent) {
		// Middle click or space+click for panning
		if (e.button === 1 || (e.button === 0 && e.altKey)) {
			isPanning = true;
			lastMousePos = { x: e.clientX, y: e.clientY };
			e.preventDefault();
			return;
		}

		// Click on background
		if (e.target === container || (e.target as HTMLElement).classList.contains('flow-layer')) {
			selectedNodeId = null;
			selectedEdgeId = null;
		}
	}

	function handleMouseMove(e: MouseEvent) {
		if (isPanning) {
			const dx = e.clientX - lastMousePos.x;
			const dy = e.clientY - lastMousePos.y;
			viewport.x += dx;
			viewport.y += dy;
			lastMousePos = { x: e.clientX, y: e.clientY };
		} else if (isDraggingNode && draggedNodeId) {
			const dx = (e.clientX - lastMousePos.x) / viewport.zoom;
			const dy = (e.clientY - lastMousePos.y) / viewport.zoom;
			
			const nodeIndex = nodes.findIndex(n => n.id === draggedNodeId);
			if (nodeIndex !== -1) {
				nodes[nodeIndex].position.x += dx;
				nodes[nodeIndex].position.y += dy;
			}
			lastMousePos = { x: e.clientX, y: e.clientY };
		} else if (connectionStart) {
			const pos = screenToFlow({ x: e.clientX, y: e.clientY });
			tempConnectionEnd = pos;
		}
	}

	function handleMouseUp() {
		if (isDraggingNode && draggedNodeId) {
			const node = nodes.find(n => n.id === draggedNodeId);
			if (node) onNodeDragStop(node);
		}
		isPanning = false;
		isDraggingNode = false;
		draggedNodeId = null;
		connectionStart = null;
		tempConnectionEnd = null;
	}

	function handleNodeMouseDown(e: MouseEvent, nodeId: string) {
		e.stopPropagation();
		// If left click and not on a control
		if (e.button === 0) {
			isDraggingNode = true;
			draggedNodeId = nodeId;
			selectedNodeId = nodeId;
			selectedEdgeId = null;
			lastMousePos = { x: e.clientX, y: e.clientY };
		}
	}

	function handleKeyDown(e: KeyboardEvent) {
		if (e.key === 'Delete' || e.key === 'Backspace') {
			if (selectedNodeId) {
				const node = nodes.find(n => n.id === selectedNodeId);
				if (node) {
					onDelete({ nodes: [node], edges: [] });
					selectedNodeId = null;
				}
			}
			if (selectedEdgeId) {
				const edge = edges.find(e => e.id === selectedEdgeId);
				if (edge) {
					onDelete({ nodes: [], edges: [edge] });
					selectedEdgeId = null;
				}
			}
		}
	}

	// --- Port Events ---

    interface ConnectEvent {
		type: 'target' | 'source';
		event: MouseEvent;
		element: HTMLElement;
	}

	function handleConnectStart(detail: ConnectEvent, nodeId: string) {
		const { type, event: mouseEvent, element } = detail;
		// element is the port element
		const rect = element.getBoundingClientRect();
		// Use center of port
		const startX = rect.left + rect.width / 2;
		const startY = rect.top + rect.height / 2;
		
		const flowPos = screenToFlow({ x: startX, y: startY });

		connectionStart = {
			nodeId,
			type,
			x: flowPos.x,
			y: flowPos.y
		};
		tempConnectionEnd = flowPos;
	}

	function handleConnectEnd(detail: ConnectEvent, targetNodeId: string) {
		if (!connectionStart) return;
		const { type } = detail;

		if (connectionStart.nodeId === targetNodeId) return; // Self connection
		if (connectionStart.type === type) return; // Same type connection

		const sourceId = connectionStart.type === 'source' ? connectionStart.nodeId : targetNodeId;
		const targetId = connectionStart.type === 'target' ? connectionStart.nodeId : targetNodeId;

		// Check if edge already exists
		if (!edges.some(e => e.source === sourceId && e.target === targetId)) {
			onConnect({ source: sourceId, target: targetId });
		}
		
		connectionStart = null;
		tempConnectionEnd = null;
	}

	// --- Rendering Edges ---

	function getEdgePath(edge: SoundboardEdge) {
		const start = getPortPosition(edge.source, 'source');
		const end = getPortPosition(edge.target, 'target');
		
		const sx = start.x;
		const sy = start.y;
		const ex = end.x;
		const ey = end.y;

		// Cubic bezier
		const midX = (sx + ex) / 2;
		return `M ${sx} ${sy} C ${midX} ${sy}, ${midX} ${ey}, ${ex} ${ey}`;
	}

	function getTempPath() {
		if (!connectionStart || !tempConnectionEnd) return '';
		const sx = connectionStart.x;
		const sy = connectionStart.y;
		const ex = tempConnectionEnd.x;
		const ey = tempConnectionEnd.y;

		// If dragging from source (right), curve goes right then left
		// If dragging from target (left), curve goes left then right
		
		// Simplify: just standard S-curve logic assuming source->target direction visual flow
		const midX = (sx + ex) / 2;
		return `M ${sx} ${sy} C ${midX} ${sy}, ${midX} ${ey}, ${ex} ${ey}`;
	}

</script>

<svelte:window onkeydown={handleKeyDown} onmouseup={handleMouseUp} onmousemove={handleMouseMove} />

<!-- svelte-ignore a11y_no_static_element_interactions -->
<div
	bind:this={container}
	class="flow-container bg-retro-bg"
	onwheel={handleWheel}
	onmousedown={handleMouseDown}
>
	<div
		class="flow-transform-layer"
		style="transform: translate({viewport.x}px, {viewport.y}px) scale({viewport.zoom});"
	>
		<!-- Edges Layer -->
		<svg class="flow-edges">
			{#each edges as edge (edge.id)}
				<!-- svelte-ignore a11y_click_events_have_key_events -->
				<path
					d={getEdgePath(edge)}
					class="edge-path"
					class:selected={edge.id === selectedEdgeId}
					onmousedown={(e) => { e.stopPropagation(); selectedEdgeId = edge.id; selectedNodeId = null; }}
				/>
			{/each}
			
			{#if connectionStart && tempConnectionEnd}
				<path d={getTempPath()} class="edge-path temp" />
			{/if}
		</svg>

		<!-- Nodes Layer -->
		<div class="flow-nodes">
			{#each nodes as node (node.id)}
				<!-- svelte-ignore a11y_no_static_element_interactions -->
				<div
					class="node-wrapper"
					style="transform: translate({node.position.x}px, {node.position.y}px);"
					onmousedown={(e) => handleNodeMouseDown(e, node.id)}
					bind:this={nodeElements[node.id]}
				>
					{#if node.type === 'sound-source'}
						<SoundSourceNode 
							{node} 
							selected={node.id === selectedNodeId} 
							onConnectStart={(e) => handleConnectStart(e, node.id)}
							onConnectEnd={(e) => handleConnectEnd(e, node.id)}
						/>
					{:else if node.type === 'playlist'}
						<PlaylistNode 
							{node} 
							selected={node.id === selectedNodeId}
							onConnectStart={(e) => handleConnectStart(e, node.id)}
							onConnectEnd={(e) => handleConnectEnd(e, node.id)}
						/>
					{:else if node.type === 'mixer'}
						<MixerNode 
							{node} 
							selected={node.id === selectedNodeId}
							onConnectStart={(e) => handleConnectStart(e, node.id)}
							onConnectEnd={(e) => handleConnectEnd(e, node.id)}
						/>
					{:else if node.type === 'output'}
						<OutputNode 
							{node} 
							selected={node.id === selectedNodeId}
							onConnectStart={(e) => handleConnectStart(e, node.id)}
							onConnectEnd={(e) => handleConnectEnd(e, node.id)}
						/>
					{/if}
				</div>
			{/each}
		</div>
	</div>
    
    <!-- Mini Controls -->
    <div class="controls absolute bottom-4 right-4 flex gap-2">
        <button class="bg-black/80 text-retro-primary border border-retro-dim px-2" onclick={() => viewport.zoom *= 1.1}>+</button>
        <button class="bg-black/80 text-retro-primary border border-retro-dim px-2" onclick={() => viewport.zoom /= 1.1}>-</button>
        <button class="bg-black/80 text-retro-primary border border-retro-dim px-2" onclick={() => { viewport.x=0; viewport.y=0; viewport.zoom=1; }}>R</button>
    </div>
</div>

<style>
	.flow-container {
		width: 100%;
		height: 100%;
		overflow: hidden;
		position: relative;
		cursor: grab;
        background-color: #1a150e;
        /* Dot grid pattern */
        background-image: radial-gradient(#4a3500 1px, transparent 1px);
        background-size: 20px 20px;
	}

    .flow-container:active {
        cursor: grabbing;
    }

	.flow-transform-layer {
		transform-origin: 0 0;
		width: 100%;
		height: 100%;
        pointer-events: none; /* Let events pass to SVG and Nodes */
	}

    .flow-edges {
        position: absolute;
        top: 0;
        left: 0;
        width: 100%;
        height: 100%;
        overflow: visible;
        pointer-events: all;
    }

	.edge-path {
		fill: none;
		stroke: var(--color-retro-dim);
		stroke-width: 2px;
        cursor: pointer;
        pointer-events: stroke;
	}

    .edge-path:hover {
        stroke: #ff9900;
    }

	.edge-path.selected {
		stroke: var(--color-retro-primary);
        stroke-width: 3px;
	}

    .edge-path.temp {
        stroke: var(--color-retro-primary);
        stroke-dasharray: 5, 5;
        opacity: 0.7;
        pointer-events: none;
    }

	.flow-nodes {
		position: absolute;
		top: 0;
		left: 0;
		width: 100%;
		height: 100%;
        pointer-events: none;
	}

	.node-wrapper {
		position: absolute;
		top: 0;
		left: 0;
        pointer-events: all;
	}
    
    .controls button:hover {
        background-color: var(--color-retro-off);
    }
</style>
