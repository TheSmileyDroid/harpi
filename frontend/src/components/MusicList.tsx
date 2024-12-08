import type { ServerError } from "@/api/ServerError";
import { useMutation, useQuery } from "@tanstack/react-query";
import { useStore } from "@tanstack/react-store";
import clsx from "clsx";
import { LoaderCircle } from "lucide-react";
import { useEffect, useState } from "react";
import apiClient from "../api/ApiClient";
import { store } from "../store";
import MusicCard from "./MusicCard";
import { Button } from "./ui/button";
import { Input } from "./ui/input";

function MusicList({className}: {className?: string}) {
  const [url, setUrl] = useState("");
  const [voiceChannel, setVoiceChannel] = useState("");

  const activeGuild = useStore(store, (state) => state.guild);

  const guildMusicState = useQuery({
    queryKey: ["musics", "guild", activeGuild?.id],
    queryFn: async () =>
      (
        await apiClient.api.getMusicStateApiGuildsStateGet({
          idx: activeGuild?.id || "-1",
        })
      ).data,
    enabled: !!activeGuild,
    refetchInterval: 10000,
  });

  useEffect(() => {
    if (guildMusicState.data?.current_voice_channel) {
      setVoiceChannel(guildMusicState.data.current_voice_channel.name);
    }
  }, [
    guildMusicState.data?.current_voice_channel,
    guildMusicState.data?.current_voice_channel?.name,
  ]);

  const addMusic = useMutation({
    mutationKey: ["musics", "add"],
    mutationFn: async (url: string) =>
      (
        await apiClient.api.addToQueueApiGuildsQueuePost({
          idx: activeGuild?.id || "-1",
          url,
        })
      ).data,
    onMutate: async () => {
      setUrl("");
      await guildMusicState.refetch();
    },
  });

  if (guildMusicState.isPending) {
    return <LoaderCircle className="animate-spin" />;
  }

  if (guildMusicState.isError) {
    return (
      <div className="text-danger">Erro ao recuperar lista de músicas</div>
    );
  }

  return (
    <div className={clsx("w-full p-3", className)}>
      <div className="p-3 space-y-2">
        <div>
          {voiceChannel.length > 0 ? (
            voiceChannel
          ) : (
            <span className="text-error">
              Harpi não está em nenhum canal de voz
            </span>
          )}
        </div>
        <div>
          <div className="flex w-full max-w-sm items-center space-x-2">
            <Input
              type="url"
              placeholder="Url"
              value={url}
              onChange={(e) => setUrl(e.target.value)}
            />
            <Button
              type="submit"
              onClick={() => addMusic.mutate(url)}
              isLoading={addMusic.isPending}
            >
              Adicionar música
            </Button>
          </div>
          {addMusic.error && (
            <div className="bg-error text-background p-1 m-1 rounded-lg w-fit text-nowrap">
              {(addMusic.error as ServerError).response?.data?.detail}
            </div>
          )}
        </div>
        {guildMusicState.data?.queue[0] && (
          <MusicCard
            music={guildMusicState.data?.queue[0]}
            duration={guildMusicState.data?.queue[0].duration}
            progress={parseInt(guildMusicState.data?.progress.toFixed(0))}
            playing={!guildMusicState.data?.paused}
            loopMode={guildMusicState.data?.loop_mode}
          />
        )}
      </div>
      <ul className="w-full">
        {guildMusicState.data?.queue.map((music, index) => {
          return (
            <li className="border shadow-md m-3 rounded-xl p-3" key={index}>
              <span className="italic">{index}</span> - {music.title} -{" "}
              {music.album}
            </li>
          );
        })}
      </ul>
    </div>
  );
}

export default MusicList;
