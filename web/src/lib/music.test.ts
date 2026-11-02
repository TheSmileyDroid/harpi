import { describe, expect, it } from "vitest";
import {
  botStateLabel,
  connectionActionLabel,
  connectionActorLabel,
  layersCountLabel,
  linkLabel,
  linkStateWord,
  outputHint,
  outputSummary,
  playbackStateLabel,
  voiceLinkLabel,
} from "./music";

describe("linkLabel", () => {
  it("names each link state", () => {
    expect(linkLabel("connected")).toBe("VÍNCULO ATIVO");
    expect(linkLabel("reconnecting")).toBe("VÍNCULO PERDIDO");
    expect(linkLabel("connecting")).toBe("VINCULANDO");
    expect(linkLabel("anything")).toBe("VINCULANDO");
  });
});

describe("linkStateWord", () => {
  it("reads as a word inside a sentence", () => {
    expect(linkStateWord("connected")).toBe("ativo");
    expect(linkStateWord("reconnecting")).toBe("perdido");
    expect(linkStateWord("connecting")).toBe("vinculando");
  });
});

describe("botStateLabel", () => {
  it("says whether the bot is on air", () => {
    expect(botStateLabel(true)).toBe("No ar");
    expect(botStateLabel(false)).toBe("Fora do ar");
  });
});

describe("voiceLinkLabel", () => {
  const base = {
    botOnline: true,
    connected: true,
    channelName: "Geral",
    channelId: "42",
  };

  it("names the connected channel", () => {
    expect(voiceLinkLabel(base)).toBe("Vinculado a Geral");
  });

  it("falls back to the channel id, then to a bare link", () => {
    expect(voiceLinkLabel({ ...base, channelName: null })).toBe(
      "Vinculado a 42",
    );
    expect(
      voiceLinkLabel({ ...base, channelName: null, channelId: null }),
    ).toBe("Vinculado");
  });

  it("reports the missing states first", () => {
    expect(voiceLinkLabel({ ...base, botOnline: false })).toBe("Indisponível");
    expect(voiceLinkLabel({ ...base, connected: false })).toBe("Sem conexão");
  });
});

describe("outputSummary", () => {
  it("asks for an output until a guild is chosen", () => {
    expect(outputSummary(null, null)).toBe("Escolha a saída");
  });

  it("joins the guild and the channel", () => {
    expect(outputSummary("Alfa", null)).toBe("Alfa");
    expect(outputSummary("Alfa", "Geral")).toBe("Alfa · Geral");
  });
});

describe("outputHint", () => {
  const ready = { botOnline: true, guildId: "1", channelId: "2" };

  it("returns nothing when the output is ready", () => {
    expect(outputHint(ready)).toBeNull();
  });

  it("names what is missing", () => {
    expect(outputHint({ ...ready, botOnline: false })).toBe("Bot fora do ar");
    expect(outputHint({ ...ready, guildId: null })).toBe("Escolha um servidor");
    expect(outputHint({ ...ready, channelId: null })).toBe("Escolha um canal");
  });
});

describe("playbackStateLabel", () => {
  const playing = {
    hasPlayback: true,
    hasTrack: true,
    isPlaying: true,
    isPaused: false,
  };

  it("separates playing, paused and stopped", () => {
    expect(playbackStateLabel(playing)).toBe("Tocando");
    expect(playbackStateLabel({ ...playing, isPaused: true })).toBe("Pausado");
    expect(playbackStateLabel({ ...playing, isPlaying: false })).toBe("Parado");
  });

  it("is stopped without a playback or a track", () => {
    expect(playbackStateLabel({ ...playing, hasPlayback: false })).toBe(
      "Parado",
    );
    expect(playbackStateLabel({ ...playing, hasTrack: false })).toBe("Parado");
  });
});

describe("layersCountLabel", () => {
  it("agrees in number", () => {
    expect(layersCountLabel(1)).toBe("1 ativa");
    expect(layersCountLabel(3)).toBe("3 ativas");
  });
});

describe("connection labels", () => {
  it("names the actor and the action", () => {
    expect(connectionActorLabel(null)).toBe("O bot");
    expect(connectionActorLabel("Ana")).toBe("Ana");
    expect(connectionActionLabel("connect")).toBe("conectou");
    expect(connectionActionLabel("disconnect")).toBe("liberou");
  });
});
