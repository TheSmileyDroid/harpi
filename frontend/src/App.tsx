import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import "./App.css";
import smileyBotLogo from "./assets/smileybot.png";
import GuildList from "./components/GuildList";
import Status from "./components/Status";

const queryClient = new QueryClient();

function App() {
  return (
    <>
      <QueryClientProvider client={queryClient}>
        <div className="h-screen w-screen">
          <div className="flex flex-wrap justify-left content-center gap-4 top-0 left-0 w-full p-2">
            <a href="/" target="_blank">
              <img
                src={smileyBotLogo}
                className="logo h-16"
                alt="SmileyDroid logo"
              />
            </a>
            <h1>Harpi Control Center</h1>
            <Status />
          </div>
          <main className="flex h-full w-full">
            <GuildList />
          </main>
        </div>
      </QueryClientProvider>
    </>
  );
}

export default App;
