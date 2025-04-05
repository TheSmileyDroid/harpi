import { LoopMode, type IMusic } from "@/api/Api";
import apiClient from "@/api/ApiClient";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { Slider } from "@/components/ui/slider";
import { store } from "@/store";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { useStore } from "@tanstack/react-store";
import clsx from "clsx";
import {
  Pause,
  Play,
  Repeat,
  Repeat1,
  SkipForward,
  Square,
} from "lucide-react";
import { motion } from "motion/react";
import { useEffect, useState } from "react";

/**
 * Componente responsável por exibir um card com a música atual e controles de reprodução.
 */
export default function MusicCard({
  music,
  className,
  progress,
  duration,
  playing,
  loopMode,
}: {
  music: IMusic;
  className?: string;
  progress: number;
  duration: number;
  playing: boolean;
  loopMode: LoopMode;
}) {
  const [_progress, setProgress] = useState(progress);
  const activeGuild = useStore(store, (state) => state.guild);

  const queryClient = useQueryClient();

  useEffect(() => {
    const interval = setInterval(() => {
      if (playing) {
        setProgress((prev) => prev + 1);
      }
    }, 1000);

    return () => clearInterval(interval);
  }, [playing]);

  useEffect(() => {
    setProgress(progress);
  }, [progress]);

  const toggleLoop = useMutation({
    onSuccess: () => {
      queryClient.invalidateQueries();
    },
    onMutate: async () => {
      return (
        await apiClient.api.loopMusicApiGuildsLoopPost(
          {
            idx: activeGuild?.id || "-1",
          },
          { mode: (loopMode + 1) % 3 }
        )
      ).data;
    },
  });

  async function handleTogglePlay() {
    if (playing) {
      await apiClient.api.pauseMusicApiGuildsPausePost({
        idx: activeGuild?.id || "-1",
      });
    } else {
      await apiClient.api.resumeMusicApiGuildsResumePost({
        idx: activeGuild?.id || "-1",
      });
    }
  }

  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.4 }}
      className={clsx("relative victorian-border", className)}
    >
      <Card className="bg-[rgba(12,12,14,0.85)] border-0 rounded-none">
        <CardContent className="p-0 w-full">
          <div className="flex flex-wrap items-center p-4 md:p-6">
            <motion.div
              className="w-24 h-24 sm:w-32 sm:h-32 flex-shrink-0 relative"
              whileHover={{ scale: 1.05 }}
              transition={{ type: "spring", stiffness: 400, damping: 10 }}
            >
              <div className="absolute inset-0 border-2 border-double border-[var(--primary)] opacity-70"></div>
              <img
                src={music.thumbnail || "/placeholder.svg?height=128&width=128"}
                alt="Album cover"
                className="object-cover h-full w-full grayscale-[70%] contrast-[1.1] brightness-[0.9]"
              />
              <div className="absolute inset-0 bg-[rgba(12,12,14,0.15)]"></div>
            </motion.div>
            <div className="flex flex-col flex-grow p-4 space-y-2 w-4/6 mx-auto">
              <motion.div layout>
                <h2 className="text-md sm:text-lg font-bold truncate tracking-wider text-[var(--primary)]">
                  {music.title} - {music.album}
                </h2>
                <p className="text-sm text-[var(--secondary)] truncate">
                  {music.artists?.join(", ") || "Artista desconhecido"}
                </p>
              </motion.div>
              <div className="space-y-1 w-5/6">
                <Slider
                  value={[_progress]}
                  max={duration}
                  step={1}
                  className="w-full"
                  onValueChange={([newValue]) => setProgress(newValue)}
                />
                <div className="flex justify-between text-xs text-[var(--secondary)]">
                  <span>
                    {Math.floor(_progress / 60)}:
                    {String(_progress % 60).padStart(2, "0")}
                  </span>
                  <span>
                    {Math.floor(duration / 60)}:
                    {String(duration % 60).padStart(2, "0")}
                  </span>
                </div>
              </div>
              <div className="flex justify-center space-x-3 mt-4 music-controls">
                <motion.div whileHover={{ scale: 1.1 }} whileTap={{ scale: 0.9 }}>
                  <Button
                    variant="outline"
                    size="icon"
                    onClick={() =>
                      apiClient.api.stopMusicApiGuildsStopPost({
                        idx: activeGuild?.id || "-1",
                      })
                    }
                  >
                    <Square className="h-4 w-4" />
                  </Button>
                </motion.div>
                <motion.div whileHover={{ scale: 1.1 }} whileTap={{ scale: 0.9 }}>
                  <Button size="icon" onClick={handleTogglePlay}>
                    {playing ? (
                      <Pause className="h-4 w-4" />
                    ) : (
                      <Play className="h-4 w-4" />
                    )}
                  </Button>
                </motion.div>
                <motion.div whileHover={{ scale: 1.1 }} whileTap={{ scale: 0.9 }}>
                  <Button
                    variant="outline"
                    size="icon"
                    onClick={() => {
                      apiClient.api.skipMusicApiGuildsSkipPost({
                        idx: activeGuild?.id || "-1",
                      });
                    }}
                  >
                    <SkipForward className="h-4 w-4" />
                  </Button>
                </motion.div>
                <motion.div whileHover={{ scale: 1.1 }} whileTap={{ scale: 0.9 }}>
                  <Button
                    variant={"outline"}
                    size={"icon"}
                    isLoading={toggleLoop.isPending}
                    className={clsx({
                      "bg-[rgba(197,199,180,0.95)] border-background text-background hover:text-[rgba(197,199,180,0.95)]/50":
                        loopMode === LoopMode.Value2 ||
                        loopMode === LoopMode.Value1,
                    })}
                    onClick={() => {
                      toggleLoop.mutate();
                    }}
                  >
                    {loopMode === LoopMode.Value2 ? (
                      <Repeat />
                    ) : loopMode === LoopMode.Value1 ? (
                      <Repeat1 />
                    ) : (
                      <Repeat />
                    )}
                  </Button>
                </motion.div>
              </div>
            </div>
          </div>
        </CardContent>
      </Card>
    </motion.div>
  );
}
