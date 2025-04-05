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
      className={clsx('guild-list', className)}
      initial={{ opacity: 0, x: -50 }}
      animate={{ opacity: 1, x: 0 }}
      transition={{ duration: 0.3 }}
    >
      <h2 className="mb-6 text-center text-lg tracking-wider opacity-80">GUILDAS</h2>
      <ul className="relative flex flex-col gap-2">
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
                  'victorian-border flex h-fit w-full flex-col text-xs shadow-[0_0_8px_rgba(0,0,0,0.2)] transition-all duration-300',
                  {
                    'bg-[rgba(197,199,180,0.15)] text-[var(--primary)] hover:bg-[rgba(197,199,180,0.1)]':
                      guild.id == activeGuild?.id,
                  }
                )}
              >
                <h3 className="text-wrap font-bold">{guild.name}</h3>
                {guild.description && <span className="opacity-70">{guild.description}</span>}
                <span className="m-1 opacity-80">Membros: {guild.approximate_member_count}</span>
              </Button>
            </motion.div>
          </motion.li>
        ))}
      </ul>
    </motion.div>
  );
}

export default GuildList;
