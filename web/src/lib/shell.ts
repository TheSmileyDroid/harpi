export type ShellLinkState = "connecting" | "connected" | "reconnecting";

type ShellRoute =
  | "/c/[campaign]/mesa"
  | "/c/[campaign]/personagens"
  | "/c/[campaign]/ficha/[[character]]"
  | "/c/[campaign]/cenas";

export interface ShellPage {
  slug: string;
  label: string;
  route: ShellRoute;
}

export const SHELL_PAGES: readonly ShellPage[] = [
  { slug: "mesa", label: "Mesa", route: "/c/[campaign]/mesa" },
  {
    slug: "personagens",
    label: "Personagens",
    route: "/c/[campaign]/personagens",
  },
  {
    slug: "ficha",
    label: "Ficha",
    route: "/c/[campaign]/ficha/[[character]]",
  },
  { slug: "cenas", label: "Cenas", route: "/c/[campaign]/cenas" },
];

export function isShellPageActive(pathname: string, slug: string): boolean {
  const segments = pathname.split("/").filter(Boolean);
  return segments[0] === "c" && segments[2] === slug;
}

export function campaignDisplayName(slug: string): string {
  return slug
    .split("-")
    .filter(Boolean)
    .map((part) => part.charAt(0).toUpperCase() + part.slice(1))
    .join(" ");
}

export function shellLinkLabel(state: ShellLinkState): string {
  if (state === "connected") return "Ativo";
  if (state === "reconnecting") return "Perdido";
  return "Conectando";
}
