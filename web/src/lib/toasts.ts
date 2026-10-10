import { writable } from "svelte/store";

export interface Toast {
  id: number;
  message: string;
  action?: ToastAction | undefined;
}

export interface ToastAction {
  label: string;
  run: () => void;
}

export interface ToastsOptions {
  schedule?: (fn: () => void, timeout: number) => unknown;
  duration?: number;
}

export function createToasts({
  schedule = setTimeout,
  duration = 4000,
}: ToastsOptions = {}) {
  const { subscribe, update } = writable<Toast[]>([]);
  let nextId = 0;

  return {
    subscribe,
    push(message: string, action?: ToastAction): number {
      const id = ++nextId;
      update((toasts) => [...toasts, { id, message, action }]);
      schedule(() => {
        update((toasts) => toasts.filter((toast) => toast.id !== id));
      }, duration);
      return id;
    },
    dismiss(id: number): void {
      update((toasts) => toasts.filter((toast) => toast.id !== id));
    },
  };
}

export const toasts = createToasts();
