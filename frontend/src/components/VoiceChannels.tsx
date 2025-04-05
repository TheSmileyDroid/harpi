import apiClient from "@/api/ApiClient";
import { store } from "@/store";
import { useMutation } from "@tanstack/react-query";
import { useStore } from "@tanstack/react-store";
import clsx from "clsx";
import { AnimatePresence, motion } from "motion/react";
import { Button } from "./ui/button";

/**
 * Componente que exibe e permite conexão aos canais de voz disponíveis.
 */
function VoiceChannels({ className }: { className?: string }) {
  const activeGuild = useStore(store, (state) => state.guild);
  const musicState = useStore(store, (state) => state.musicState);

  const enterVoiceChannel = useMutation({
    mutationKey: ["voice_channels", "enter"],
    mutationFn: async (channelId: string) =>
      apiClient.api.connectToVoiceApiGuildsVoiceConnectPost({
        idx: activeGuild?.id || "-1",
        channel_id: channelId,
      }),
  });

  return (
    <motion.div
      className={clsx("p-3 shadow-lg mx-auto", className)}
      initial={{ opacity: 0, scale: 0.95 }}
      animate={{ opacity: 1, scale: 1 }}
      transition={{ duration: 0.4 }}
    >
      <div className="p-0">
        <AnimatePresence>
          {activeGuild?.voice_channels?.map((channel, index) => (
            <motion.div
              key={channel.id}
              className="flex border shadow-md m-3 p-3 justify-around content-center gap-3"
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: -20 }}
              transition={{ delay: index * 0.1, duration: 0.3 }}
              whileHover={{
                scale: 1.02,
                boxShadow: "0 10px 15px -3px rgba(0, 0, 0, 0.1)"
              }}
            >
              <span className="w-full my-auto">
                {channel.name}
                {channel.id == musicState?.current_voice_channel?.id && (
                  <motion.span
                    className="text-primary mx-2"
                    initial={{ opacity: 0 }}
                    animate={{ opacity: 1 }}
                    transition={{ duration: 0.3 }}
                  >
                    (Conectado)
                  </motion.span>
                )}
              </span>
              <motion.div whileHover={{ scale: 1.05 }} whileTap={{ scale: 0.95 }}>
                <Button
                  onClick={() => {
                    enterVoiceChannel.mutate(channel.id);
                  }}
                  variant={"outline"}
                  size={"lg"}
                  className={clsx("my-auto", {
                    "bg-primary text-background hover:bg-primary/15":
                      channel.id == musicState?.current_voice_channel?.id,
                  })}
                  isLoading={enterVoiceChannel.isPending}
                >
                  {channel.id == musicState?.current_voice_channel?.id
                    ? "Reconectar"
                    : "Conectar"}
                </Button>
              </motion.div>
            </motion.div>
          ))}
        </AnimatePresence>
      </div>
    </motion.div>
  );
}

export default VoiceChannels;
