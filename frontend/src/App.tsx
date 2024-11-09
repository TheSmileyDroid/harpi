import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { PanelLeftOpen, PanelRightOpen, SunMoon } from "lucide-react";
import { useEffect, useState } from "react";
import "./App.css";
import smileyBotLogo from "./assets/smileybot.png";
import GuildList from "./components/GuildList";
import MusicList from "./components/MusicList";
import Status from "./components/Status";
import { Button } from "./components/ui/button";
import {
  Collapsible,
  CollapsibleContent,
  CollapsibleTrigger,
} from "./components/ui/collapsible";

const queryClient = new QueryClient();

function App() {
  const [theme, setTheme] = useState("dark");

  const [openGuilds, setOpenGuilds] = useState(false);

  const switchTheme = () => {
    setTheme((prevTheme) => (prevTheme === "dark" ? "light" : "dark"));
  };

  useEffect(() => {
    document.documentElement.setAttribute("data-theme", theme);
  }, [theme]);

  return (
    <>
      <QueryClientProvider client={queryClient}>
        <div className={"h-screen w-screen bg-background text-foreground"}>
          <div className="flex flex-wrap justify-left content-center  gap-4 top-0 left-0 w-full p-2">
            <a href="/" target="_blank">
              <img
                src={smileyBotLogo}
                className="logo h-16"
                alt="SmileyDroid logo"
              />
            </a>
            <h1 className="text-2xl content-center">Harpi Control Center</h1>
            <Status />
            <Button onClick={switchTheme} size={"icon"} className="self-center">
              <SunMoon />
            </Button>
          </div>
          <main className="flex h-full w-full">
            <Collapsible
              open={openGuilds}
              onOpenChange={setOpenGuilds}
              defaultOpen
            >
              <CollapsibleTrigger>
                <div className="p-2">
                  {openGuilds ? <PanelRightOpen /> : <PanelLeftOpen />}
                </div>
              </CollapsibleTrigger>
              <CollapsibleContent forceMount>
                <GuildList
                  className={`
                  transition-all transform duration-300
                  ${
                    openGuilds
                      ? "opacity-100 translate-x-0 max-w-full"
                      : "opacity-0 -translate-x-full pointer-events-none max-w-0 overflow-hidden"
                  }
                `}
                />
              </CollapsibleContent>
            </Collapsible>

            <MusicList />
          </main>
        </div>
      </QueryClientProvider>
    </>
  );
}

export default App;
