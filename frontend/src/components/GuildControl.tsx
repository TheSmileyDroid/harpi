import { store } from "@/store";
import { useStore } from "@tanstack/react-store";
import MusicList from "./MusicList";

function GuildControl() {
  const activeGuild = useStore(store, (state) => state.guild);

  return (
    <div className="w-full p-3">
      <div className="p-0">
        <div className="flex border shadow-md m-3 rounded-xl p-3 justify-center content-center gap-3">
          <span className="font-bold text-lg my-auto">Controle de guilda</span>
          {activeGuild?.name ? (
            <div className="border rounded-xl p-3 border-dashed">
              <span className="italic">Guilda ativa:</span> {activeGuild?.name}
            </div>
          ) : (
            <div className="border rounded-xl p-3 border-dashed border-error">
              <span className="italic">Nenhuma guilda ativa</span>
            </div>
          )}
        </div>
      </div>
      {activeGuild?.id && <MusicList />}
    </div>
  );
}

export default GuildControl;
