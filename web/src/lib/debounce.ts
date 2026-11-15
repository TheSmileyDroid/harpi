type Timer = ReturnType<typeof setTimeout>;

export interface Debouncer {
  run(fn: () => void): void;
  cancel(): void;
}

export function createDebouncer(delay: number): Debouncer {
  let timer: Timer | null = null;
  return {
    run(fn) {
      if (timer !== null) clearTimeout(timer);
      timer = setTimeout(() => {
        timer = null;
        fn();
      }, delay);
    },
    cancel() {
      if (timer !== null) clearTimeout(timer);
      timer = null;
    },
  };
}
