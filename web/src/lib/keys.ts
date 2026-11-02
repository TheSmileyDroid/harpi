export function isEditableTarget(target: EventTarget | null): boolean {
  if (typeof target !== "object" || target === null) return false;
  const element = target as { tagName?: unknown; isContentEditable?: unknown };
  if (element.isContentEditable === true) return true;
  return (
    typeof element.tagName === "string" &&
    ["INPUT", "TEXTAREA", "SELECT"].includes(element.tagName)
  );
}
