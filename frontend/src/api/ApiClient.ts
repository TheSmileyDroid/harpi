import { Api } from "./Api";

const apiClient = new Api({
  baseURL: import.meta.env.PROD ? undefined : "http://localhost:8000",
  withCredentials: true,
});

export default apiClient;
