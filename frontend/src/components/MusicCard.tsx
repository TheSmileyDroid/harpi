import type { IMusic } from "@/api/Api";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { Slider } from "@/components/ui/slider";
import clsx from "clsx";
import { Pause, Play, SkipBack, SkipForward } from "lucide-react";
import { useEffect, useState } from "react";

export default function MusiCard({
  music,
  className,
}: {
  music: IMusic;
  className?: string;
}) {
  const [playing, setPlaying] = useState(true);
  const [progress, setProgress] = useState(0);
  const [duration, setDuration] = useState(3 * 60);

  useEffect(() => {
    const interval = setInterval(() => {
      if (playing) {
        setProgress((prev) => prev + 1);
      }
    }, 1000);

    return () => clearInterval(interval);
  }, [playing]);

  function togglePlayPause() {
    setPlaying((prev) => !prev);
  }

  return (
    <Card className={clsx("", className)}>
      <CardContent className="p-0">
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
                {music.title}
              </h2>
              <p className="text-sm text-muted-foreground truncate">
                {music.artist || "Unknown Artist"}
              </p>
            </div>
            <div className="space-y-1 w-full">
              <Slider
                value={[progress]}
                max={duration}
                step={1}
                className="w-full"
                onValueChange={([newValue]) => setProgress(newValue)}
              />
              <div className="flex justify-between text-xs text-muted-foreground">
                <span>
                  {Math.floor(progress / 60)}:
                  {String(progress % 60).padStart(2, "0")}
                </span>
                <span>
                  {Math.floor(duration / 60)}:
                  {String(duration % 60).padStart(2, "0")}
                </span>
              </div>
            </div>
            <div className="flex justify-center space-x-2">
              <Button variant="outline" size="icon">
                <SkipBack className="h-4 w-4" />
              </Button>
              <Button size="icon" onClick={togglePlayPause}>
                {playing ? (
                  <Pause className="h-4 w-4" />
                ) : (
                  <Play className="h-4 w-4" />
                )}
              </Button>
              <Button variant="outline" size="icon">
                <SkipForward className="h-4 w-4" />
              </Button>
            </div>
          </div>
        </div>
      </CardContent>
    </Card>
  );
}
