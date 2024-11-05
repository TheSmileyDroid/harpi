import { Api } from "./Api";

const apiClient = new Api({
  baseURL: import.meta.env.DEV ? "http://localhost:8000" : undefined,
  withCredentials: true,
});

export default apiClient;
