import { describe, expect, it } from "vitest";
import { isEditableTarget } from "./keys";

describe("keyboard targets", () => {
  it("treats fields and editable regions as shortcut blockers", () => {
    expect(isEditableTarget({ tagName: "INPUT" } as never)).toBe(true);
    expect(isEditableTarget({ tagName: "TEXTAREA" } as never)).toBe(true);
    expect(isEditableTarget({ tagName: "SELECT" } as never)).toBe(true);
    expect(
      isEditableTarget({ tagName: "DIV", isContentEditable: true } as never),
    ).toBe(true);
    expect(isEditableTarget({ tagName: "BUTTON" } as never)).toBe(false);
    expect(isEditableTarget(null)).toBe(false);
  });
});
