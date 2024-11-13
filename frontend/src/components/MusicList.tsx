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
    <div className="w-full p-3">
      <div className="p-3">
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
            <li className="border shadow-md m-3 rounded-xl p-3">
              <span className="italic">{index}</span> - {music.title}
            </li>
          );
        })}
      </ul>
    </div>
  );
}

export default MusicList;
