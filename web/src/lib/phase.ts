import { ApiError } from "./api";

export type LoadPhase =
  "loading" | "ready" | "not_found" | "unavailable" | "failed";

export function phaseForError(error: unknown): LoadPhase {
  if (error instanceof ApiError) {
    if (error.code === "vault_unavailable") return "unavailable";
    if (error.status === 404) return "not_found";
  }
  return "failed";
}
