import { formatCount } from "./format";

export function linkLabel(state: string): string {
  if (state === "connected") return "VÍNCULO ATIVO";
  if (state === "reconnecting") return "VÍNCULO PERDIDO";
  return "VINCULANDO";
}

export function linkStateWord(state: string): string {
  if (state === "connected") return "ativo";
  if (state === "reconnecting") return "perdido";
  return "vinculando";
}

export function botStateLabel(online: boolean): string {
  return online ? "No ar" : "Fora do ar";
}

export function voiceLinkLabel(input: {
  botOnline: boolean;
  connected: boolean;
  channelName: string | null;
  channelId: string | null;
}): string {
  if (!input.botOnline) return "Indisponível";
  if (!input.connected) return "Sem conexão";
  const target = input.channelName ?? input.channelId;
  return target ? `Vinculado a ${target}` : "Vinculado";
}

export function outputSummary(
  guildName: string | null,
  channelName: string | null,
): string {
  if (!guildName) return "Escolha a saída";
  return `${guildName}${channelName ? ` · ${channelName}` : ""}`;
}

export function outputHint(input: {
  botOnline: boolean;
  guildId: string | null;
  channelId: string | null;
}): string | null {
  if (!input.botOnline) return "Bot fora do ar";
  if (input.guildId === null) return "Escolha um servidor";
  if (input.channelId === null) return "Escolha um canal";
  return null;
}

export function playbackStateLabel(input: {
  hasPlayback: boolean;
  hasTrack: boolean;
  isPlaying: boolean;
  isPaused: boolean;
}): string {
  if (!input.hasPlayback || !input.hasTrack || !input.isPlaying) {
    return "Parado";
  }
  return input.isPaused ? "Pausado" : "Tocando";
}

export function layersCountLabel(count: number): string {
  return formatCount(count, "ativa", "ativas");
}

export function connectionActorLabel(name: string | null): string {
  return name ?? "O bot";
}

export function connectionActionLabel(action: string): string {
  return action === "connect" ? "conectou" : "liberou";
}
