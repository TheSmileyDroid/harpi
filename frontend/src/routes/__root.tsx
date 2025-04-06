import { useEffect, useState } from 'react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { createRootRoute, Link, useMatch, useMatches } from '@tanstack/react-router';
import { Menu, PanelLeftOpen, PanelRightOpen, X } from 'lucide-react';
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
    const [openGuilds, setOpenGuilds] = useState(false);
    // eslint-disable-next-line react-hooks/rules-of-hooks
    const [mobileMenuOpen, setMobileMenuOpen] = useState(false);
    // eslint-disable-next-line react-hooks/rules-of-hooks
    const matches = useMatches();
    // eslint-disable-next-line react-hooks/rules-of-hooks
    const match = useMatch({ strict: false });
    const nextMatchIndex = matches.findIndex((d) => d.id === match.id) + 1;
    const nextMatch = matches[nextMatchIndex];

    // eslint-disable-next-line react-hooks/rules-of-hooks
    useEffect(() => {
      // Configurar estado inicial baseado no tamanho da tela
      const handleResize = () => {
        if (window.innerWidth >= 1024) {
          setOpenGuilds(true);
        } else {
          setOpenGuilds(false);
        }
      };

      // Executar na montagem e quando a janela for redimensionada
      handleResize();
      window.addEventListener('resize', handleResize);

      return () => {
        window.removeEventListener('resize', handleResize);
      };
    }, []);

    // Fechar o menu mobile quando uma rota é alterada
    // eslint-disable-next-line react-hooks/rules-of-hooks
    useEffect(() => {
      setMobileMenuOpen(false);
    }, [match.id]);

    return (
      <QueryClientProvider client={queryClient}>
        <div className="noise-bg flex h-full w-screen flex-col p-1 sm:p-2">
          <header className="victorian-border rounded-none">
            <div className="flex items-center gap-2 sm:gap-4">
              <motion.a
                className="my-auto"
                whileHover={{ scale: 1.1, rotate: 5 }}
                whileTap={{ scale: 0.9 }}
              >
                <img
                  src={smileyBotLogo}
                  className="h-8 brightness-[0.9] contrast-[1.2] grayscale-[50%] md:h-12 lg:h-16"
                  alt="SmileyDroid logo"
                />
              </motion.a>
              <motion.h1
                className="hidden text-sm font-bold sm:block sm:text-base md:text-lg"
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                transition={{ delay: 0.2 }}
              >
                Harpi Control Center
              </motion.h1>

              {/* Menu Mobile */}
              <Button
                size={'icon'}
                variant={'outline'}
                className="nier-button ml-auto lg:hidden"
                onClick={() => setMobileMenuOpen(!mobileMenuOpen)}
              >
                {mobileMenuOpen ? <X size={18} /> : <Menu size={18} />}
              </Button>

              {/* Menu Desktop */}
              <div className="ml-4 hidden gap-3 lg:flex">
                <Link
                  to="/"
                  className="nier-button px-3 py-1 text-sm [&.active]:bg-[rgba(197,199,180,0.2)]"
                  activeProps={{ className: 'active' }}
                >
                  Início
                </Link>
                <Link
                  to="/system"
                  className="nier-button px-3 py-1 text-sm [&.active]:bg-[rgba(197,199,180,0.2)]"
                  activeProps={{ className: 'active' }}
                >
                  Sistema
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

            {/* Menu mobile expandido */}
            <AnimatePresence>
              {mobileMenuOpen && (
                <motion.div
                  className="flex flex-col gap-2 py-3 lg:hidden"
                  initial={{ opacity: 0, height: 0 }}
                  animate={{ opacity: 1, height: 'auto' }}
                  exit={{ opacity: 0, height: 0 }}
                  transition={{ duration: 0.2 }}
                >
                  <Link
                    to="/"
                    className="nier-button px-3 py-1 text-sm [&.active]:bg-[rgba(197,199,180,0.2)]"
                    activeProps={{ className: 'active' }}
                  >
                    Início
                  </Link>
                  <Link
                    to="/system"
                    className="nier-button px-3 py-1 text-sm [&.active]:bg-[rgba(197,199,180,0.2)]"
                    activeProps={{ className: 'active' }}
                  >
                    Sistema
                  </Link>
                  <Link
                    to="/about"
                    className="nier-button px-3 py-1 text-sm [&.active]:bg-[rgba(197,199,180,0.2)]"
                    activeProps={{ className: 'active' }}
                  >
                    Sobre
                  </Link>
                </motion.div>
              )}
            </AnimatePresence>

            <div className="flex items-center gap-2">
              <Status />
              <motion.div whileHover={{ scale: 1.05 }} whileTap={{ scale: 0.95 }}>
                <Button
                  size={'sm'}
                  variant={'outline'}
                  className="nier-button sm:size-default self-center text-xs sm:text-sm"
                  onClick={() => setOpenGuilds((prev) => !prev)}
                >
                  <span className="hidden sm:inline">Guildas</span>{' '}
                  {openGuilds ? <PanelRightOpen size={18} /> : <PanelLeftOpen size={18} />}
                </Button>
              </motion.div>
            </div>
          </header>
          <main className="flex h-full w-screen overflow-hidden">
            <AnimatePresence>
              {openGuilds && (
                <motion.div
                  className="sidebar z-10 m-3 h-full w-[250px] border sm:w-[280px] md:w-[300px] lg:relative lg:h-auto"
                  initial={{ opacity: 0 }}
                  animate={{ opacity: 1 }}
                  exit={{ opacity: 0 }}
                  layoutId="sidebar"
                  layout
                  transition={{ type: 'spring', stiffness: 300, damping: 30 }}
                >
                  <div className="flex justify-end lg:hidden">
                    <Button
                      size={'sm'}
                      variant={'ghost'}
                      onClick={() => setOpenGuilds(false)}
                      className="mb-2"
                    >
                      <X size={18} />
                    </Button>
                  </div>
                  <GuildList className="h-full" />
                </motion.div>
              )}
            </AnimatePresence>
            <motion.div
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              whileInView={{ opacity: 1 }}
              layout
              layoutId="main"
              transition={{ type: 'spring', stiffness: 300, damping: 30, duration: 0.2 }}
              key={nextMatch.id + 'main'}
              className="h-full w-full overflow-y-auto p-2 sm:p-4"
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
