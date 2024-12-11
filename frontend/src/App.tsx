import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { PanelLeftOpen, PanelRightOpen, SunMoon } from "lucide-react";
import { useEffect, useState } from "react";
import "./App.css";
import smileyBotLogo from "./assets/smileybot.png";
import GuildControl from "./components/GuildControl";
import GuildList from "./components/GuildList";
import Status from "./components/Status";
import { Button } from "./components/ui/button";

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
        <div className={"h-full w-screen"}>
          <div className="w-5/6 md:w-full mx-auto">
            <div className="flex flex-wrap justify-left content-center gap-2 top-0 left-0 m-2">
              <a href="/" target="_blank" className="my-auto">
                <img
                  src={smileyBotLogo}
                  className="h-8 md:h-16"
                  alt="SmileyDroid logo"
                />
              </a>
              <h1 className="text-md font-bold content-center">
                Harpi Control Center
              </h1>
              <Status />
              <Button
                onClick={switchTheme}
                size={"icon"}
                className="self-center"
              >
                <SunMoon />
              </Button>
              <Button
                size={"default"}
                variant={"outline"}
                className="self-center"
                onClick={() => setOpenGuilds((prev) => !prev)}
              >
                Guildas {openGuilds ? <PanelRightOpen /> : <PanelLeftOpen />}
              </Button>
            </div>
          </div>
          <main className="flex h-full w-screen">
            <div className="absolute">
              <GuildList
                className={`
                    transition-all transform duration-300 bg-background border rounded-r-2xl p-1 shadow-2xl mr-5
                    ${
                      openGuilds
                        ? "opacity-100 translate-x-0 translate-y-0 max-w-full"
                        : "opacity-0 -translate-x-full pointer-events-none max-w-0 overflow-hidden"
                    }
                  `}
              />
            </div>
            <GuildControl />
          </main>
        </div>
      </QueryClientProvider>
    </>
  );
}

export default App;
