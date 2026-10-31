import { describe, expect, it } from "vitest";
import { ApiError } from "./api";
import { phaseForError } from "./phase";

function failure(code: string, status: number): ApiError {
  return new ApiError({ code, message: "Failed", status });
}

describe("phaseForError", () => {
  it("reads a missing resource as not found", () => {
    expect(phaseForError(failure("not_found", 404))).toBe("not_found");
  });

  it("reads a missing vault as unavailable", () => {
    expect(phaseForError(failure("vault_unavailable", 503))).toBe(
      "unavailable",
    );
  });

  it("reads anything else as a failure", () => {
    expect(phaseForError(failure("internal_error", 500))).toBe("failed");
    expect(phaseForError(new Error("offline"))).toBe("failed");
  });
});
