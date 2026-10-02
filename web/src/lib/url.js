const URL_PATTERN = /^https?:\/\/\S+$/i;

export function looksLikeUrl(value) {
  return URL_PATTERN.test(value.trim());
}
