import { Api } from "./Api";

const apiClient = new Api({
  baseURL: import.meta.env.PROD ? undefined : "http://localhost:8000",
  withCredentials: true,
});

export const BASE_URL = import.meta.env.PROD
  ? window.location.host
  : "localhost:8000";

export default apiClient;
