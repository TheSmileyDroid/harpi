import { useEffect, useState } from 'react';
import { useMutation, useQueryClient } from '@tanstack/react-query';
import { useStore } from '@tanstack/react-store';
import clsx from 'clsx';
import { Music, Pause, Play, Repeat, Repeat1, SkipForward, Square } from 'lucide-react';
import { motion } from 'motion/react';
import { LoopMode, type IMusic } from '@/api/Api';
import apiClient from '@/api/ApiClient';
import { Button } from '@/components/ui/button';
import { Card, CardContent } from '@/components/ui/card';
import { Slider } from '@/components/ui/slider';
import { store } from '@/store';

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
  const [imageError, setImageError] = useState(false);
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
          { idx: activeGuild?.id || '-1' },
          { mode: (loopMode + 1) % 3 }
        )
      ).data;
    },
  });

  async function handleTogglePlay() {
    if (playing) {
      await apiClient.api.pauseMusicApiGuildsPausePost({ idx: activeGuild?.id || '-1' });
    } else {
      await apiClient.api.resumeMusicApiGuildsResumePost({ idx: activeGuild?.id || '-1' });
    }
  }

  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.4 }}
      className={clsx('victorian-border relative', className)}
    >
      <Card className="rounded-none border-0 bg-[rgba(12,12,14,0.85)]">
        <CardContent className="w-full p-0">
          <div className="flex flex-wrap items-center p-4 md:p-6">
            <motion.div
              className="relative h-24 w-24 flex-shrink-0 sm:h-32 sm:w-32"
              whileHover={{ scale: 1.05 }}
              transition={{ type: 'spring', stiffness: 400, damping: 10 }}
            >
              <div className="absolute inset-0 border-2 border-double border-[var(--primary)] opacity-70"></div>
              {!music.thumbnail || imageError ? (
                <div className="flex h-full w-full items-center justify-center bg-[rgba(12,12,14,0.8)]">
                  <Music className="h-12 w-12 text-[var(--primary)]" />
                </div>
              ) : (
                <img
                  src={music.thumbnail}
                  alt="Album cover"
                  className="h-full w-full object-cover brightness-[0.9] contrast-[1.1] grayscale-[70%]"
                  onError={() => setImageError(true)}
                />
              )}
              <div className="absolute inset-0 bg-[rgba(12,12,14,0.15)]"></div>
            </motion.div>
            <div className="mx-auto flex w-4/6 flex-grow flex-col space-y-2 p-4">
              <motion.div layout>
                <h2 className="text-md truncate font-bold tracking-wider text-[var(--primary)] sm:text-lg">
                  {music.title} - {music.album}
                </h2>
                <p className="truncate text-sm text-[var(--secondary)]">
                  {music.artists?.join(', ') || 'Artista desconhecido'}
                </p>
              </motion.div>
              <div className="w-5/6 space-y-1">
                <Slider
                  value={[_progress]}
                  max={duration}
                  step={1}
                  className="w-full"
                  onValueChange={([newValue]) => setProgress(newValue)}
                />
                <div className="flex justify-between text-xs text-[var(--secondary)]">
                  <span>
                    {Math.floor(_progress / 60)}:{String(_progress % 60).padStart(2, '0')}
                  </span>
                  <span>
                    {Math.floor(duration / 60)}:{String(duration % 60).padStart(2, '0')}
                  </span>
                </div>
              </div>
              <div className="music-controls mt-4 flex justify-center space-x-3">
                <motion.div whileHover={{ scale: 1.1 }} whileTap={{ scale: 0.9 }}>
                  <Button
                    variant="outline"
                    size="icon"
                    onClick={() =>
                      apiClient.api.stopMusicApiGuildsStopPost({ idx: activeGuild?.id || '-1' })
                    }
                  >
                    <Square className="h-4 w-4" />
                  </Button>
                </motion.div>
                <motion.div whileHover={{ scale: 1.1 }} whileTap={{ scale: 0.9 }}>
                  <Button size="icon" onClick={handleTogglePlay}>
                    {playing ? <Pause className="h-4 w-4" /> : <Play className="h-4 w-4" />}
                  </Button>
                </motion.div>
                <motion.div whileHover={{ scale: 1.1 }} whileTap={{ scale: 0.9 }}>
                  <Button
                    variant="outline"
                    size="icon"
                    onClick={() => {
                      apiClient.api.skipMusicApiGuildsSkipPost({ idx: activeGuild?.id || '-1' });
                    }}
                  >
                    <SkipForward className="h-4 w-4" />
                  </Button>
                </motion.div>
                <motion.div whileHover={{ scale: 1.1 }} whileTap={{ scale: 0.9 }}>
                  <Button
                    variant={'outline'}
                    size={'icon'}
                    isLoading={toggleLoop.isPending}
                    className={clsx({
                      'border-background bg-[rgba(197,199,180,0.95)] text-background hover:text-[rgba(197,199,180,0.95)]/50':
                        loopMode === LoopMode.Value2 || loopMode === LoopMode.Value1,
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
