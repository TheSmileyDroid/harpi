import type { ServerError } from "@/api/ServerError";
import { useMutation, useQuery } from "@tanstack/react-query";
import { useStore } from "@tanstack/react-store";
import clsx from "clsx";
import { LoaderCircle } from "lucide-react";
import { AnimatePresence, motion } from "motion/react";
import { useEffect, useState } from "react";
import apiClient from "../api/ApiClient";
import { setMusicState, store } from "../store";
import MusicCard from "./MusicCard";
import { Button } from "./ui/button";
import { Input } from "./ui/input";

/**
 * Componente que exibe a lista de músicas e controles para adicionar novas músicas.
 */
function MusicList({ className }: { className?: string }) {
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
    setMusicState(guildMusicState.data);
  }, [guildMusicState.data]);

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
    return (
      <motion.div
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        className="flex justify-center items-center h-40"
      >
        <LoaderCircle className="animate-spin" />
      </motion.div>
    );
  }

  if (guildMusicState.isError) {
    return (
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        className="text-danger"
      >
        Erro ao recuperar lista de músicas
      </motion.div>
    );
  }

  return (
    <div className={clsx("w-3/6 p-3 mx-auto", className)}>
      <motion.div
        className="p-3 space-y-2 w-full mx-auto"
        initial={{ opacity: 0, y: -20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.3 }}
      >
        <div className="flex justify-center items-center w-full ">
          {voiceChannel.length > 0 ? (
            <motion.div
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              transition={{ delay: 0.2 }}
            >
              {voiceChannel}
            </motion.div>
          ) : (
            <motion.span
              className="text-error text-wrap"
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              transition={{ delay: 0.2 }}
            >
              Harpi não está em nenhum canal de voz
            </motion.span>
          )}
        </div>
        <motion.div
          initial={{ opacity: 0, y: 10 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.3 }}
        >
          <div className="flex w-full max-w-[80%] space-x-2 mx-auto">
            <Input
              type="url"
              placeholder="Url"
              className="w-full"
              value={url}
              onChange={(e) => setUrl(e.target.value)}
            />
            <motion.div whileHover={{ scale: 1.05 }} whileTap={{ scale: 0.95 }}>
              <Button
                type="submit"
                onClick={() => addMusic.mutate(url)}
                isLoading={addMusic.isPending}
              >
                Adicionar música
              </Button>
            </motion.div>
          </div>
          <AnimatePresence>
            {addMusic.error && (
              <motion.div
                className="bg-error text-background p-1 m-1 w-fit text-wrap"
                initial={{ opacity: 0, height: 0 }}
                animate={{ opacity: 1, height: "auto" }}
                exit={{ opacity: 0, height: 0 }}
              >
                {(addMusic.error as ServerError).response?.data?.detail}
              </motion.div>
            )}
          </AnimatePresence>
        </motion.div>
        {guildMusicState.data?.queue[0] && (
          <MusicCard
            music={guildMusicState.data?.queue[0]}
            duration={guildMusicState.data?.queue[0].duration}
            progress={parseInt(guildMusicState.data?.progress.toFixed(0))}
            playing={!guildMusicState.data?.paused}
            loopMode={guildMusicState.data?.loop_mode}
          />
        )}
      </motion.div>
      <motion.ul
        className="w-full h-56 overflow-y-auto border shadow-md p-3 mx-auto"
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        transition={{ delay: 0.4 }}
      >
        <AnimatePresence>
          {guildMusicState.data?.queue.map((music, index) => {
            return (
              <motion.li
                className="border shadow-md m-3 p-3"
                key={index}
                initial={{ opacity: 0, x: -20 }}
                animate={{ opacity: 1, x: 0 }}
                exit={{ opacity: 0, x: 20 }}
                transition={{ delay: index * 0.05 }}
                whileHover={{ scale: 1.02, boxShadow: "0 10px 15px -3px rgba(0, 0, 0, 0.1)" }}
              >
                <span className="italic">{index}</span> - {music.title} -{" "}
                {music.album}
              </motion.li>
            );
          })}
        </AnimatePresence>
      </motion.ul>
    </div>
  );
}

export default MusicList;
