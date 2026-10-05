const URL_PATTERN = /^https?:\/\/\S+$/i;

export function looksLikeUrl(value: string): boolean {
  return URL_PATTERN.test(value.trim());
}
