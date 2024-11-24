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
import { useEffect, useState } from "react";

export default function MusiCard({
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
    <Card className={clsx("bg-background", className)}>
      <CardContent className="p-0 w-full ">
        <div className="flex items-center px-6">
          <div className="w-24 h-24 sm:w-32 sm:h-32 flex-shrink-0">
            <img
              src={music.thumbnail || "/placeholder.svg?height=128&width=128"}
              alt="Album cover"
              className="object-cover h-full w-full rounded-2xl"
            />
          </div>
          <div className="flex flex-col flex-grow p-4 space-y-2">
            <div>
              <h2 className="text-lg sm:text-xl font-bold truncate">
                {music.title} - {music.album}
              </h2>
              <p className="text-sm text-foreground truncate">
                {music.artists?.join(", ") || "Artista desconhecido"}
              </p>
            </div>
            <div className="space-y-1 w-full">
              <Slider
                value={[_progress]}
                max={duration}
                step={1}
                className="w-full"
                onValueChange={([newValue]) => setProgress(newValue)}
              />
              <div className="flex justify-between text-xs text-foreground">
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
            <div className="flex justify-center space-x-2">
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
              <Button size="icon" onClick={handleTogglePlay}>
                {playing ? (
                  <Pause className="h-4 w-4" />
                ) : (
                  <Play className="h-4 w-4" />
                )}
              </Button>
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
              <Button
                variant={"outline"}
                size={"icon"}
                isLoading={toggleLoop.isPending}
                className={clsx({
                  "bg-accent hover:bg-accent/50":
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
            </div>
          </div>
        </div>
      </CardContent>
    </Card>
  );
}
