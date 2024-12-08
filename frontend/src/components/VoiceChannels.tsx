import { store } from "@/store";
import { useStore } from "@tanstack/react-store";
import clsx from "clsx";

function VoiceChannels({ className }: { className?: string }) {
  const activeGuild = useStore(store, (state) => state.guild);



  return (
    <div className={clsx("p-3 shadow-lg rounded-lg", className)}>
        <div className="p-0">
            {activeGuild?.voice_channels?.map((channel) => (
                <div key={channel.id} className="flex border shadow-md m-3 rounded-xl p-3 justify-center content-center gap-3">
                    <span className="font-bold text-lg my-auto">{channel.name}</span>
                    <span className="font-bold text-lg my-auto">{channel.members.length}</span>
                </div>
            ))}
        </div>

    </div>
  );
}

export default VoiceChannels;
