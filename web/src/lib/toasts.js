import { writable } from "svelte/store";

/**
 * @typedef {object} ToastsOptions
 * @property {(handler: () => void, timeout?: number) => any} [schedule]
 * @property {number} [duration]
 */

/**
 * @param {ToastsOptions} [options]
 */
export function createToasts({ schedule = setTimeout, duration = 4000 } = {}) {
  const { subscribe, update } = writable([]);
  let nextId = 0;

  return {
    subscribe,
    push(message) {
      const id = ++nextId;
      update((toasts) => [...toasts, { id, message }]);
      schedule(() => {
        update((toasts) => toasts.filter((toast) => toast.id !== id));
      }, duration);
      return id;
    },
    dismiss(id) {
      update((toasts) => toasts.filter((toast) => toast.id !== id));
    },
  };
}

export const toasts = createToasts();
