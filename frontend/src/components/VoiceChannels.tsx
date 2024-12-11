import apiClient from "@/api/ApiClient";
import { store } from "@/store";
import { useMutation } from "@tanstack/react-query";
import { useStore } from "@tanstack/react-store";
import clsx from "clsx";
import { Button } from "./ui/button";

function VoiceChannels({ className }: { className?: string }) {
  const activeGuild = useStore(store, (state) => state.guild);

  const enterVoiceChannel = useMutation({
    mutationKey: ["voice_channels", "enter"],
    mutationFn: async (channelId: string) =>
      apiClient.api.connectToVoiceApiGuildsVoiceConnectPost({
        idx: activeGuild?.id || "-1",
        channel_id: channelId,
      }),
  });

  return (
    <div className={clsx("p-3 shadow-lg rounded-lg mx-auto", className)}>
      <div className="p-0">
        {activeGuild?.voice_channels?.map((channel) => (
          <div
            key={channel.id}
            className="flex border shadow-md m-3 rounded-xl p-3 justify-around content-center gap-3"
          >
            <span className="my-auto">{channel.name}</span>
            <Button
              onClick={() => {
                enterVoiceChannel.mutate(channel.id);
              }}
              variant={"outline"}
              size={"lg"}
              className={clsx("my-auto")}
              isLoading={enterVoiceChannel.isPending}
            >
              Entrar
            </Button>
          </div>
        ))}
      </div>
    </div>
  );
}

export default VoiceChannels;
