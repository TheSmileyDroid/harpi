import axios from "axios";

const BASE_URL = import.meta.env.PROD ? "" : "http://127.0.0.1:8000";

export const api = axios.create({
  baseURL: BASE_URL + "/api",
  withCredentials: true,
});

interface IStatus {
  status: string;
}

export async function getStatus() {
  const { data } = await api.get<IStatus>("/status");
  return data;
}
