import { useQuery } from "@tanstack/react-query";
import { useStore } from "@tanstack/react-store";
import clsx from "clsx";
import apiClient from "../api/ApiClient";
import { setGuild, store } from "../store";
import { Button } from "./ui/button";
function GuildList({ className = "" }: { className?: string }) {
  const activeGuild = useStore(store, (state) => state.guild);

  const query = useQuery({
    queryKey: ["guilds"],
    queryFn: async () => (await apiClient.api.getApiGuildsGet()).data,
  });

  return (
    <div className={clsx(className)}>
      <ul className="flex flex-col gap-1 m-1">
        {query.data?.map((guild) => (
          <li key={guild.id}>
            <Button
              onClick={() => {
                setGuild(guild);
              }}
              variant={"outline"}
              size={"lg"}
              className={clsx(
                "card shadow-md h-fit flex flex-col w-full transition-all duration-300",
                {
                  "bg-primary text-white hover:bg-primary/15":
                    guild.id == activeGuild?.id,
                }
              )}
            >
              <h3 className="font-bold">{guild.name}</h3>
              {guild.description && ` - ${guild.description}`}
              <span className="m-1">
                Membros: {guild.approximate_member_count}
              </span>
            </Button>
          </li>
        ))}
      </ul>
    </div>
  );
}

export default GuildList;
