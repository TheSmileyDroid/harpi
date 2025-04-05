import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { PanelLeftOpen, PanelRightOpen } from "lucide-react";
import { AnimatePresence, motion } from "motion/react";
import { useState } from "react";
import "./App.css";
import smileyBotLogo from "./assets/smileybot.png";
import GuildControl from "./components/GuildControl";
import GuildList from "./components/GuildList";
import Status from "./components/Status";
import { Button } from "./components/ui/button";

const queryClient = new QueryClient();

/**
 * Componente principal da aplicação.
 *
 * Responsável por renderizar o layout principal e gerenciar o estado global.
 */
function App() {
  const [openGuilds, setOpenGuilds] = useState(false);

  return (
    <>
      <QueryClientProvider client={queryClient}>
        <div className="h-full w-screen noise-bg">
          <header className="victorian-border rounded-none">
            <div className="flex items-center gap-4">
              <motion.a
                href="/"
                target="_blank"
                className="my-auto"
                whileHover={{ scale: 1.1, rotate: 5 }}
                whileTap={{ scale: 0.9 }}
              >
                <img
                  src={smileyBotLogo}
                  className="h-8 md:h-16 brightness-[0.9] contrast-[1.2] grayscale-[50%]"
                  alt="SmileyDroid logo"
                />
              </motion.a>
              <motion.h1
                className="text-md font-bold content-center"
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                transition={{ delay: 0.2 }}
              >
                Harpi Control Center
              </motion.h1>
            </div>
            <div className="flex items-center gap-2">
              <Status />
              <motion.div whileHover={{ scale: 1.05 }} whileTap={{ scale: 0.95 }}>
                <Button
                  size={"default"}
                  variant={"outline"}
                  className="self-center nier-button"
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
                  transition={{
                    type: "spring",
                    stiffness: 300,
                    damping: 30
                  }}
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
              <GuildControl />
            </motion.div>
          </main>
        </div>
      </QueryClientProvider>
    </>
  );
}

export default App;
