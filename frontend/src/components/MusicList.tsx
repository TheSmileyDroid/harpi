import type { ServerError } from "@/api/ServerError";
import { useMutation, useQuery } from "@tanstack/react-query";
import { useStore } from "@tanstack/react-store";
import { LoaderCircle } from "lucide-react";
import { useState } from "react";
import apiClient from "../api/ApiClient";
import { store } from "../store";
import MusicCard from "./MusicCard";
import { Button } from "./ui/button";
import { Input } from "./ui/input";

function MusicList() {
  const [url, setUrl] = useState("");
  const activeGuild = useStore(store, (state) => state.guild);

  const musicList = useQuery({
    queryKey: ["musics", "guild", activeGuild?.id],
    queryFn: async () =>
      (
        await apiClient.api.getMusicStateApiGuildsStateGet({
          idx: activeGuild?.id || "-1",
        })
      ).data,
    enabled: !!activeGuild,
    refetchInterval: 5000,
  });

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
      await musicList.refetch();
    },
  });

  if (musicList.isPending) {
    return <LoaderCircle className="animate-spin" />;
  }

  if (musicList.isError) {
    return (
      <div className="text-danger">Erro ao recuperar lista de músicas</div>
    );
  }

  return (
    <div className="w-full p-3">
      <div className="p-3 space-y-2">
        <div>
          <div className="flex w-full max-w-sm items-center space-x-2">
            <Input
              type="url"
              placeholder="Url"
              onChange={(e) => setUrl(e.target.value)}
            />
            <Button type="submit" onClick={() => addMusic.mutate(url)}>
              Adicionar música
            </Button>
          </div>
          {addMusic.error && (
            <div className="bg-error text-background p-1 m-1 rounded-lg w-fit text-nowrap">
              {(addMusic.error as ServerError).response?.data?.detail}
            </div>
          )}
        </div>
        {musicList.data?.queue[0] && (
          <MusicCard
            music={musicList.data?.queue[0]}
            duration={musicList.data?.queue[0].duration}
            progress={parseInt(musicList.data?.progress.toFixed(0))}
          />
        )}
      </div>
      <ul className="w-full">
        {musicList.data?.queue.map((music, index) => {
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
