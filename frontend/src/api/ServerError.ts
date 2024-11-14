import type { AxiosError } from "axios";

export interface ApiError {
  detail: string;
}

export type ServerError = AxiosError<ApiError>;
