import type { FlipParams } from "svelte/animate";
import { cubicOut } from "svelte/easing";

export function flipParams(): FlipParams {
  return window.matchMedia("(prefers-reduced-motion: reduce)").matches
    ? { duration: 0 }
    : { duration: 200, easing: cubicOut };
}
