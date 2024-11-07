import { useQuery } from "@tanstack/react-query";
import { useStore } from "@tanstack/react-store";
import apiClient from "../api/ApiClient";
import { store } from "../store";

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
  });

  if (musicList.isFetching || musicList.isLoading) {
    return <span>Carregando...</span>;
  }

  if (musicList.isError) {
    return <div>Erro ao recuperar lista de músicas</div>;
  }

  return (
    <div>
      <h3>Tocando agora: {musicList.data?.queue[0]?.title}</h3>
      {musicList.data?.queue.map((music) => {
        return <div>{music.title}</div>;
      })}
    </div>
  );
}

export default MusicList;
