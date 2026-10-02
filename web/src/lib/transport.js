const LOOP_CYCLE = { OFF: "track", TRACK: "queue", QUEUE: "off" };

/**
 * @param {number} value
 * @param {number} min
 * @param {number} max
 */
function clamp(value, min, max) {
  return Math.min(Math.max(value, min), max);
}

/**
 * Pointer x as a 0-1 ratio along a track of *width* pixels.
 *
 * @param {number} offsetX
 * @param {number} width
 * @returns {number}
 */
export function pointerRatio(offsetX, width) {
  if (!Number.isFinite(width) || width <= 0) return 0;
  if (!Number.isFinite(offsetX)) return 0;
  return clamp(offsetX / width, 0, 1);
}

/**
 * Absolute seek target in seconds for a 0-1 ratio along the track.
 *
 * @param {number} ratio
 * @param {number} duration
 * @returns {number}
 */
export function seekTarget(ratio, duration) {
  if (!Number.isFinite(duration) || duration <= 0) return 0;
  if (!Number.isFinite(ratio)) return 0;
  return clamp(ratio, 0, 1) * duration;
}

/**
 * 0-1 ratio to paint the seek bar: the pointer preview while dragging, the
 * clamped server ratio otherwise. A live server frame never moves the bar
 * mid-drag.
 *
 * @param {boolean} seeking
 * @param {number} seekRatio
 * @param {number} serverRatio
 * @returns {number}
 */
export function seekDisplayRatio(seeking, seekRatio, serverRatio) {
  const ratio = seeking ? seekRatio : serverRatio;
  if (!Number.isFinite(ratio)) return 0;
  return clamp(ratio, 0, 1);
}

/**
 * Perceptual slider position 0-1 to linear gain (ADR 0002: gain = pos²).
 *
 * @param {number} position
 * @returns {number}
 */
export function volumeGain(position) {
  if (!Number.isFinite(position)) return 0;
  return clamp(position, 0, 1) ** 2;
}

/**
 * Linear gain to perceptual slider position 0-1 (inverse of volumeGain).
 *
 * @param {number} gain
 * @returns {number}
 */
export function volumePosition(gain) {
  if (!Number.isFinite(gain)) return 0;
  return Math.sqrt(clamp(gain, 0, 1));
}

/**
 * Next loop mode in the OFF -> TRACK -> QUEUE -> OFF cycle.
 *
 * @param {string} mode
 * @returns {string}
 */
export function nextLoopMode(mode) {
  return LOOP_CYCLE[mode] ?? "off";
}
