/**
 * @typedef {object} Debouncer
 * @property {(fn: () => void) => void} run
 * @property {() => void} cancel
 */

/**
 * @typedef {object} DebouncerOptions
 * @property {number} [delay]
 * @property {(fn: () => void, timeout: number) => any} [schedule]
 * @property {(id: any) => void} [cancel]
 */

/**
 * @param {DebouncerOptions} [options]
 * @returns {Debouncer}
 */
export function createDebouncer({
  delay = 300,
  schedule = setTimeout,
  cancel = clearTimeout,
} = {}) {
  let timer = null;
  return {
    run(fn) {
      if (timer !== null) cancel(timer);
      timer = schedule(() => {
        timer = null;
        fn();
      }, delay);
    },
    cancel() {
      if (timer !== null) cancel(timer);
      timer = null;
    },
  };
}
