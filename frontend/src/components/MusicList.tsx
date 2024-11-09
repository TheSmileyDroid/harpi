import { useQuery } from "@tanstack/react-query";
import { useStore } from "@tanstack/react-store";
import { LoaderCircle } from "lucide-react";
import apiClient from "../api/ApiClient";
import { store } from "../store";
import MusicCard from "./MusicCard";

function MusicList() {
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
  });

  if (musicList.isFetching || musicList.isLoading) {
    return <LoaderCircle className="animate-spin" />;
  }

  if (musicList.isError) {
    return (
      <div className="text-danger">Erro ao recuperar lista de músicas</div>
    );
  }

  return (
    <div>
      <div className="">
        {musicList.data?.queue[0] && (
          <MusicCard music={musicList.data?.queue[0]} className="h-40 w-full" />
        )}
      </div>
      {musicList.data?.queue.map((music) => {
        return <div>{music.title}</div>;
      })}
    </div>
  );
}

export default MusicList;
