import { store } from "@/store";
import { useStore } from "@tanstack/react-store";
import clsx from "clsx";
import MusicList from "./MusicList";
import VoiceChannels from "./VoiceChannels";

function GuildControl({ className }: { className?: string }) {
  const activeGuild = useStore(store, (state) => state.guild);

  return (
    <div className={clsx("w-full", className)}>
      <div className="p-0 w-5/6 mx-auto">
        <div className="flex flex-wrap text-sm border shadow-md m-3 rounded-xl p-3 justify-center content-center gap-3">
          <span className="font-bold my-auto">Controle de guilda</span>
          {activeGuild?.name ? (
            <div className="border rounded-xl p-3 border-dashed">
              <span className="italic ">Guilda ativa:</span> {activeGuild?.name}
            </div>
          ) : (
            <div className="border rounded-xl p-3 border-dashed border-error">
              <span className="italic text-error font-bold">
                Nenhuma guilda ativa
              </span>
            </div>
          )}
        </div>
      </div>
      {activeGuild?.id && (
        <div className="flex flex-wrap w-5/6 mx-auto">
          <MusicList className="flex-grow" />
          <VoiceChannels className="flex-shrink" />
        </div>
      )}
    </div>
  );
}

export default GuildControl;
