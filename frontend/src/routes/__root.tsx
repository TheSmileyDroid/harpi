import { useState } from 'react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { createRootRoute, Link, useMatch, useMatches } from '@tanstack/react-router';
import { PanelLeftOpen, PanelRightOpen } from 'lucide-react';
import { AnimatePresence, motion } from 'motion/react';
import smileyBotLogo from '@/assets/smileybot.png';
import AnimatedOutlet from '@/components/AnimatedOutlet';
import GuildList from '@/components/GuildList';
import Status from '@/components/Status';
import { Button } from '@/components/ui/button';

const queryClient = new QueryClient();

export const Route = createRootRoute({
  component: () => {
    // eslint-disable-next-line react-hooks/rules-of-hooks
    const [openGuilds, setOpenGuilds] = useState(true);
    // eslint-disable-next-line react-hooks/rules-of-hooks
    const matches = useMatches();
    // eslint-disable-next-line react-hooks/rules-of-hooks
    const match = useMatch({ strict: false });
    const nextMatchIndex = matches.findIndex((d) => d.id === match.id) + 1;
    const nextMatch = matches[nextMatchIndex];

    return (
      <QueryClientProvider client={queryClient}>
        <div className="noise-bg h-full w-screen">
          <header className="victorian-border rounded-none">
            <div className="flex items-center gap-4">
              <motion.a
                className="my-auto"
                whileHover={{ scale: 1.1, rotate: 5 }}
                whileTap={{ scale: 0.9 }}
              >
                <img
                  src={smileyBotLogo}
                  className="h-8 brightness-[0.9] contrast-[1.2] grayscale-[50%] md:h-16"
                  alt="SmileyDroid logo"
                />
              </motion.a>
              <motion.h1
                className="text-md content-center font-bold"
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                transition={{ delay: 0.2 }}
              >
                Harpi Control Center
              </motion.h1>
              <div className="ml-4 flex gap-3">
                <Link
                  to="/"
                  className="nier-button px-3 py-1 text-sm [&.active]:bg-[rgba(197,199,180,0.2)]"
                  activeProps={{ className: 'active' }}
                >
                  Início
                </Link>
                <Link
                  to="/about"
                  className="nier-button px-3 py-1 text-sm [&.active]:bg-[rgba(197,199,180,0.2)]"
                  activeProps={{ className: 'active' }}
                >
                  Sobre
                </Link>
              </div>
            </div>
            <div className="flex items-center gap-2">
              <Status />
              <motion.div whileHover={{ scale: 1.05 }} whileTap={{ scale: 0.95 }}>
                <Button
                  size={'default'}
                  variant={'outline'}
                  className="nier-button self-center"
                  onClick={() => setOpenGuilds((prev) => !prev)}
                >
                  Guildas {openGuilds ? <PanelRightOpen /> : <PanelLeftOpen />}
                </Button>
              </motion.div>
            </div>
          </header>
          <main className="flex h-full w-screen">
            <AnimatePresence>
              {openGuilds && (
                <motion.div
                  className="sidebar victorian-border"
                  initial={{ opacity: 0, x: -300 }}
                  animate={{ opacity: 1, x: 0 }}
                  exit={{ opacity: 0, x: -300 }}
                  transition={{ type: 'spring', stiffness: 300, damping: 30 }}
                >
                  <GuildList className="guild-list" />
                </motion.div>
              )}
            </AnimatePresence>
            <motion.div
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              transition={{ delay: 0.3, duration: 0.5 }}
              className="w-full p-4"
            >
              <AnimatePresence mode="popLayout">
                <AnimatedOutlet key={nextMatch.id} />
              </AnimatePresence>
            </motion.div>
          </main>
        </div>
      </QueryClientProvider>
    );
  },
});
