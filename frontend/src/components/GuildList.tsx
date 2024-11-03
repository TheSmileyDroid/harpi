import { useQuery } from "@tanstack/react-query";
import clsx from "clsx";
import { getGuilds } from "../api/guild/api";

function GuildList({ className = "" }: { className?: string }) {
  const query = useQuery({ queryKey: ["guilds"], queryFn: getGuilds });

  return (
    <div className={clsx(className)}>
      <ul>
        {query.data?.map((guild) => (
          <li key={guild.id} className="card shadow-md">
            {guild.name} - {guild.description}
          </li>
        ))}
      </ul>
    </div>
  );
}

export default GuildList;
