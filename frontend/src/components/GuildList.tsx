import { useQuery } from "@tanstack/react-query";
import clsx from "clsx";
import apiClient from "../api/ApiClient";
function GuildList({ className = "" }: { className?: string }) {
  const query = useQuery({
    queryKey: ["guilds"],
    queryFn: async () => (await apiClient.api.getApiGuildsGet()).data,
  });

  return (
    <div className={clsx(className)}>
      <ul>
        {query.data?.map((guild) => (
          <li key={guild.id} className="card shadow-md flex flex-col">
            <h3 className="font-bold">{guild.name}</h3>
            {guild.description && ` - ${guild.description}`}
            <span className="m-3">
              Membros: {guild.approximate_member_count}
            </span>
          </li>
        ))}
      </ul>
    </div>
  );
}

export default GuildList;
