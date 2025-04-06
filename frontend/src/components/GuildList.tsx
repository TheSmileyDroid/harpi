import { useQuery } from '@tanstack/react-query';
import { useStore } from '@tanstack/react-store';
import clsx from 'clsx';
import { motion } from 'motion/react';
import apiClient from '../api/ApiClient';
import { setGuild, store } from '../store';
import { Button } from './ui/button';

/**
 * Componente que exibe a lista de guildas disponíveis.
 */
function GuildList({ className = '' }: { className?: string }) {
  const activeGuild = useStore(store, (state) => state.guild);

  const query = useQuery({
    queryKey: ['guilds'],
    queryFn: async () => (await apiClient.api.getApiGuildsGet()).data,
  });

  return (
    <motion.div
      className={clsx('guild-list flex flex-col', className)}
      initial={{ opacity: 0, x: -50 }}
      animate={{ opacity: 1, x: 0 }}
      transition={{ duration: 0.3 }}
    >
      <h2 className="mb-4 text-center text-base tracking-wider opacity-80 sm:mb-6 sm:text-lg">
        GUILDAS
      </h2>
      <ul className="flex w-full flex-col gap-2 p-4">
        {query.data?.map((guild, index) => (
          <motion.li
            key={guild.id}
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: index * 0.05, duration: 0.2 }}
            className="relative"
            whileHover={{ scale: 1.03 }}
          >
            <motion.div
              className="victorian-element"
              whileHover={{ scale: 1.03 }}
              whileTap={{ scale: 0.97 }}
            >
              <Button
                onClick={() => {
                  setGuild(guild);
                }}
                variant={'outline'}
                size={'lg'}
                className={clsx(
                  'victorian-border flex h-fit w-full flex-col p-2 text-xs shadow-[0_0_8px_rgba(0,0,0,0.2)] transition-all duration-300 sm:p-3 md:text-sm',
                  {
                    'bg-[rgba(197,199,180,0.15)] text-[var(--primary)] hover:bg-[rgba(197,199,180,0.1)]':
                      guild.id == activeGuild?.id,
                  }
                )}
              >
                <h3 className="line-clamp-1 text-wrap font-bold">{guild.name}</h3>
                {guild.description && (
                  <span className="line-clamp-2 opacity-70">{guild.description}</span>
                )}
                <span className="m-1 text-xs opacity-80">
                  Membros: {guild.approximate_member_count}
                </span>
              </Button>
            </motion.div>
          </motion.li>
        ))}
        {query.isLoading && (
          <div className="flex justify-center p-4">
            <div className="h-6 w-6 animate-spin rounded-full border-b-2 border-t-2 border-[var(--primary)]"></div>
          </div>
        )}
        {query.data?.length === 0 && (
          <div className="flex justify-center p-4 text-center text-xs sm:text-sm">
            <p>Nenhuma guilda encontrada.</p>
          </div>
        )}
      </ul>
    </motion.div>
  );
}

export default GuildList;
