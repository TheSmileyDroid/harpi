import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { PanelLeftOpen, PanelRightOpen, SunMoon } from "lucide-react";
import { useEffect, useState } from "react";
import "./App.css";
import smileyBotLogo from "./assets/smileybot.png";
import GuildControl from "./components/GuildControl";
import GuildList from "./components/GuildList";
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
        <div className={"h-full w-full"}>
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
            <div className="absolute">
              <Collapsible
                open={openGuilds}
                onOpenChange={setOpenGuilds}
                defaultOpen
              >
                <CollapsibleTrigger>
                  <Button className="m-2" size={"icon"}>
                    {openGuilds ? <PanelRightOpen /> : <PanelLeftOpen />}
                  </Button>
                </CollapsibleTrigger>
                <CollapsibleContent forceMount>
                  <GuildList
                    className={`
                    transition-all transform duration-300 bg-background border rounded-r-2xl p-4 shadow-2xl
                    ${
                      openGuilds
                        ? "opacity-100 translate-x-0 translate-y-0 max-w-full"
                        : "opacity-0 -translate-x-full pointer-events-none max-w-0 overflow-hidden"
                    }
                  `}
                  />
                </CollapsibleContent>
              </Collapsible>
            </div>
            <GuildControl className="ml-10" />
          </main>
        </div>
      </QueryClientProvider>
    </>
  );
}

export default App;
