import { api } from "../api";

interface IGuild {
  id: number;
  name: string;
  description: string;
}

export async function getGuilds() {
  const { data } = await api.get<IGuild[]>("/guilds");
  return data;
}
