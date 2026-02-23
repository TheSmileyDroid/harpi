// Soundboard Types

export type NodeType = 'sound-source' | 'playlist' | 'mixer' | 'output';

export interface SoundboardNodeData {
	url?: string;
	volume: number;
	loop?: boolean;
	title?: string;
	duration?: number;
	thumbnail?: string;
	items?: PlaylistItem[];
	currentIndex?: number;
	label?: string;
	[key: string]: unknown;
}

export interface PlaylistItem {
	url: string;
	title: string;
	duration: number;
}

export interface SoundboardNode {
	id: string;
	type: NodeType;
	data: SoundboardNodeData;
	position: { x: number; y: number };
}

export interface SoundboardEdge {
	id: string;
	source: string;
	target: string;
}

export interface SoundboardGraph {
	nodes: SoundboardNode[];
	edges: SoundboardEdge[];
}

export interface ActiveNodeStatus {
	nodeId: string;
	layerId: string;
	playing: boolean;
	volume: number;
	progress: number;
	duration: number;
	title: string;
	url: string;
}

export interface SoundboardStatus {
	connected: boolean;
	channelId: number | null;
	channelName: string | null;
	activeNodes: ActiveNodeStatus[];
	graph: SoundboardGraph | null;
}

export interface MetadataResponse {
	title: string;
	duration: number;
	url: string;
	thumbnail: string | null;
	error: string | null;
}
