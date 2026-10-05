export interface BotStatus {
  online: boolean;
}

export interface Connection {
  connected: boolean;
  channel_id: string | null;
}

export interface Guild {
  id: string;
  name: string;
}

export interface Channel {
  id: string;
  name: string;
}

export interface Track {
  url: string;
  title: string;
  uploader: string;
  duration: number;
  thumbnail: string;
}

export interface Layer {
  id: string;
  title: string;
  url: string;
  thumbnail: string;
  volume: number;
}

export interface PlaybackStatus {
  guild_id: string | null;
  connected: boolean;
  is_playing: boolean;
  is_paused: boolean;
  current_music: Track | null;
  queue: Track[];
  layers: Layer[];
  loop_mode: string;
  volume: number;
  progress: number;
  channel_id: string | null;
}

export interface StatusSnapshot {
  bot: BotStatus;
  guild_id: string | null;
  connection: Connection;
  playback: PlaybackStatus | null;
}

export interface Authenticated {
  authenticated: boolean;
}

export interface GuildList {
  guilds: Guild[];
}

export interface ChannelList {
  channels: Channel[];
}

export interface SearchResults {
  results: Track[];
}

interface ReloadEvent {
  scope: string;
}

export interface StatusFrame {
  type: "status";
  data: StatusSnapshot;
}

export interface ReloadFrame {
  type: "reload";
  data: ReloadEvent;
}

export type SseFrame = StatusFrame | ReloadFrame;
