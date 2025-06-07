import { useEffect, useState } from 'react';
import { useMutation, useQuery } from '@tanstack/react-query';
import { useStore } from '@tanstack/react-store';
import clsx from 'clsx';
import { ExternalLink, LoaderCircle } from 'lucide-react';
import { AnimatePresence, motion } from 'motion/react';
import type { ServerError } from '@/api/ServerError';
import apiClient from '../api/ApiClient';
import { setMusicState, store } from '../store';
import MusicCard from './MusicCard';
import { Button } from './ui/button';
import { Input } from './ui/input';

/**
 * Componente que exibe a lista de músicas e controles para adicionar novas músicas.
 */
function MusicList({ className }: { className?: string }) {
  const [url, setUrl] = useState('');
  const [voiceChannel, setVoiceChannel] = useState('');
  const [isFullscreenOpen, setIsFullscreenOpen] = useState(false);

  const activeGuild = useStore(store, (state) => state.guild);

  const guildMusicState = useQuery({
    queryKey: ['musics', 'guild', activeGuild?.id],
    queryFn: async () =>
      (
        await apiClient.api.getMusicStateApiGuildsStateGet({
          idx: activeGuild?.id || '-1',
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
    mutationKey: ['musics', 'add'],
    mutationFn: async (url: string) =>
      (
        await apiClient.api.addToQueueApiGuildsQueuePost({
          idx: activeGuild?.id || '-1',
          url,
        })
      ).data,
    onMutate: async () => {
      setUrl('');
      await guildMusicState.refetch();
    },
  });

  if (guildMusicState.isPending) {
    return (
      <motion.div
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        className="flex h-40 items-center justify-center"
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
    <div className={clsx('mx-auto w-3/6 p-3', className)}>
      <motion.div
        className="mx-auto w-full space-y-2 p-3"
        initial={{ opacity: 0, y: -20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.3 }}
      >
        <div className="flex w-full items-center justify-center">
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
              className="text-wrap text-error"
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
          <div className="mx-auto flex w-full max-w-[80%] space-x-2">
            <Input
              type="url"
              placeholder="Url"
              className="w-full"
              value={url}
              onChange={(e) => setUrl(e.target.value)}
              onKeyDown={(e) => {
                if (e.key === 'Enter' && url.trim()) {
                  addMusic.mutate(url);
                }
              }}
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
                className="m-1 w-fit text-wrap bg-error p-1 text-background"
                initial={{ opacity: 0, height: 0 }}
                animate={{ opacity: 1, height: 'auto' }}
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
      <div className="relative">
        <motion.ul
          className="mx-auto h-56 w-full overflow-y-auto border p-3 shadow-md"
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          transition={{ delay: 0.4 }}
        >
          <motion.div
            className="absolute right-0 top-0 bg-background"
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            transition={{ delay: 0.5 }}
          >
            <Button
              variant="outline"
              size="icon"
              className="nier-button h-8 w-8 sm:h-9 sm:w-9"
              onClick={() => setIsFullscreenOpen(true)}
            >
              <ExternalLink className="h-3 w-3 sm:h-4 sm:w-4" />
            </Button>
          </motion.div>
          <AnimatePresence>
            {guildMusicState.data?.queue.map((music, index) => {
              return (
                <motion.li
                  className="m-3 border p-3 shadow-md"
                  key={index}
                  initial={{ opacity: 0, x: -20 }}
                  animate={{ opacity: 1, x: 0 }}
                  exit={{ opacity: 0, x: 20 }}
                  transition={{ delay: index * 0.05 }}
                  whileHover={{ scale: 1.02, boxShadow: '0 10px 15px -3px rgba(0, 0, 0, 0.1)' }}
                >
                  <span className="italic">{index}</span> - {music.title} - {music.album}
                </motion.li>
              );
            })}
          </AnimatePresence>
        </motion.ul>
      </div>

      {/* Modal de lista de músicas em tela cheia */}
      <AnimatePresence>
        {isFullscreenOpen && (
          <motion.div
            className="bg-background/80 fixed inset-0 z-50 flex items-center justify-center backdrop-blur-sm"
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
          >
            <motion.div
              className="victorian-border relative h-[80vh] w-[80vw] overflow-hidden bg-background p-6"
              initial={{ scale: 0.9, opacity: 0 }}
              animate={{ scale: 1, opacity: 1 }}
              exit={{ scale: 0.9, opacity: 0 }}
              transition={{ type: 'spring', stiffness: 300, damping: 30 }}
            >
              <Button
                variant="outline"
                className="nier-button absolute right-4 top-4"
                onClick={() => setIsFullscreenOpen(false)}
              >
                Fechar
              </Button>
              <h2 className="mb-4 text-center text-xl font-bold text-primary">
                Lista de Reprodução
              </h2>
              <div className="h-full overflow-y-auto p-4">
                <ul className="mb-12 space-y-4">
                  {guildMusicState.data?.queue.map((music, index) => (
                    <motion.li
                      key={index}
                      className="nier-card p-4"
                      initial={{ opacity: 0, y: 10 }}
                      animate={{ opacity: 1, y: 0 }}
                      transition={{ delay: index * 0.05 }}
                      whileHover={{
                        scale: 1.02,
                        transition: { duration: 0.2 },
                      }}
                    >
                      <div className="flex items-center gap-4">
                        <span className="text-2xl font-semibold text-secondary">{index}</span>
                        <div className="flex-1">
                          <h3 className="text-lg font-bold text-primary">{music.title}</h3>
                          <p className="text-secondary">{music.album}</p>
                          <p className="text-sm text-neutral-400">
                            {music.artists?.join(', ') || 'Artista desconhecido'} •
                            {Math.floor(music.duration / 60)}:
                            {String(music.duration % 60).padStart(2, '0')}
                          </p>
                        </div>
                      </div>
                    </motion.li>
                  ))}
                </ul>
              </div>
            </motion.div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}

export default MusicList;
