type Timer = ReturnType<typeof setTimeout>;

export interface Debouncer {
  run(fn: () => void): void;
  cancel(): void;
}

export interface DebouncerOptions {
  delay?: number;
  schedule?: (fn: () => void, timeout: number) => Timer;
  cancel?: (id: Timer) => void;
}

export function createDebouncer({
  delay = 300,
  schedule = setTimeout,
  cancel = clearTimeout,
}: DebouncerOptions = {}): Debouncer {
  let timer: Timer | null = null;
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
