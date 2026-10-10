<script lang="ts">
  interface SelectOption {
    id: string;
    label: string;
  }

  let {
    options,
    value = null,
    placeholder = "Select",
    disabled = false,
    label,
    testid = "select",
    optionTestid = "select-option",
    onchange,
  }: {
    options: SelectOption[];
    value?: string | null;
    placeholder?: string;
    disabled?: boolean;
    label: string;
    testid?: string;
    optionTestid?: string;
    onchange: (id: string | null) => void;
  } = $props();

  let open = $state(false);
  let activeIndex = $state(-1);
  let root = $state<HTMLElement | null>(null);
  let typed = "";
  let typedTimer: ReturnType<typeof setTimeout> | null = null;

  const listId = $derived(`${testid}-listbox`);
  const selected = $derived(options.find((option) => option.id === value));
  const display = $derived(selected ? selected.label : placeholder);
  const activeOption = $derived(options[activeIndex] ?? null);

  function openList() {
    if (disabled) return;
    open = true;
    const current = options.findIndex((option) => option.id === value);
    activeIndex = current === -1 ? 0 : current;
  }

  function closeList() {
    open = false;
    activeIndex = -1;
  }

  function focusTrigger() {
    root?.querySelector<HTMLButtonElement>(".hud-select__trigger")?.focus();
  }

  function choose(option: SelectOption) {
    onchange(option.id);
    closeList();
    focusTrigger();
  }

  function move(delta: number) {
    if (options.length === 0) return;
    if (!open) {
      openList();
      return;
    }
    activeIndex = (activeIndex + delta + options.length) % options.length;
  }

  function typeahead(key: string) {
    if (typedTimer !== null) clearTimeout(typedTimer);
    typed += key.toLowerCase();
    typedTimer = setTimeout(() => (typed = ""), 500);
    if (!open) openList();
    const start = typed.length === 1 ? activeIndex + 1 : activeIndex;
    for (let offset = 0; offset < options.length; offset += 1) {
      const index = (start + offset + options.length) % options.length;
      const option = options[index];
      if (option && option.label.toLowerCase().startsWith(typed)) {
        activeIndex = index;
        return;
      }
    }
  }

  function onKeydown(event: KeyboardEvent) {
    if (disabled) return;
    if (event.key === "ArrowDown") {
      event.preventDefault();
      move(1);
    } else if (event.key === "ArrowUp") {
      event.preventDefault();
      move(-1);
    } else if (event.key === "Home" && open && options.length > 0) {
      event.preventDefault();
      activeIndex = 0;
    } else if (event.key === "End" && open && options.length > 0) {
      event.preventDefault();
      activeIndex = options.length - 1;
    } else if (event.key === "Enter" || event.key === " ") {
      event.preventDefault();
      if (open && activeOption) choose(activeOption);
      else openList();
    } else if (event.key === "Escape" && open) {
      event.preventDefault();
      event.stopPropagation();
      closeList();
    } else if (event.key === "Tab") {
      closeList();
    } else if (
      event.key.length === 1 &&
      !event.metaKey &&
      !event.ctrlKey &&
      !event.altKey
    ) {
      typeahead(event.key);
    }
  }

  function onWindowClick(event: MouseEvent) {
    if (open && root && !root.contains(event.target as Node)) closeList();
  }

  $effect(() => {
    if (!open || !root) return;
    const index = activeIndex;
    root
      .querySelector<HTMLElement>(`[data-index="${index}"]`)
      ?.scrollIntoView({ block: "nearest" });
  });
</script>

<svelte:window onclick={onWindowClick} />

<div class="hud-select" class:is-open={open} bind:this={root}>
  <button
    type="button"
    class="hud-select__trigger"
    role="combobox"
    aria-haspopup="listbox"
    aria-expanded={open}
    aria-controls={listId}
    aria-label={label}
    aria-activedescendant={open && activeOption
      ? `${testid}-option-${activeIndex}`
      : undefined}
    {disabled}
    onclick={() => (open ? closeList() : openList())}
    onkeydown={onKeydown}
    data-testid={testid}
  >
    <span class="hud-select__value" class:is-placeholder={!selected}>
      {display}
    </span>
    <span class="hud-select__chevron" aria-hidden="true"></span>
  </button>

  {#if open}
    <ul class="hud-select__list" id={listId} role="listbox" aria-label={label}>
      {#each options as option, index (option.id)}
        <li
          class="hud-select__option"
          class:is-active={index === activeIndex}
          role="option"
          aria-selected={option.id === value}
          id={`${testid}-option-${index}`}
          data-index={index}
          data-testid={optionTestid}
          onpointerdown={() => choose(option)}
          onmousemove={() => (activeIndex = index)}
        >
          {option.label}
        </li>
      {/each}
    </ul>
  {/if}
</div>

<style>
  .hud-select {
    position: relative;
    min-width: 0;
  }

  .hud-select__trigger {
    position: relative;
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 0.5rem;
    width: 100%;
    background: transparent;
    border: 1px solid var(--color-line);
    color: var(--color-primary);
    font-size: 0.8rem;
    padding: 0.35rem 0.6rem;
    text-align: start;
    cursor: pointer;
  }

  .hud-select__trigger:hover {
    border-color: var(--color-amber-dim);
  }

  .hud-select__trigger:disabled {
    color: var(--color-idle);
    cursor: not-allowed;
  }

  .hud-select__value {
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
  }

  .hud-select__value.is-placeholder {
    color: var(--color-amber-dim);
  }

  .hud-select__chevron {
    flex: none;
    width: 0.4rem;
    height: 0.4rem;
    border-right: 1px solid var(--color-amber-dim);
    border-bottom: 1px solid var(--color-amber-dim);
    transform: rotate(45deg) translate(-0.1rem, -0.1rem);
  }

  .hud-select__list {
    position: absolute;
    inset-block-start: calc(100% + 0.35rem);
    inset-inline: 0;
    z-index: 50;
    margin: 0;
    padding: 0;
    list-style: none;
    max-height: 16rem;
    overflow-y: auto;
    background: var(--color-surface);
    border: 1px solid var(--color-line);
    outline: 1px solid var(--color-line-strong);
    outline-offset: 2px;
  }

  .hud-select__option {
    padding: 0.4rem 0.6rem;
    font-size: 0.8rem;
    color: var(--color-primary);
    border-bottom: 1px solid var(--color-line);
    cursor: pointer;
  }

  .hud-select__option:last-child {
    border-bottom: none;
  }

  .hud-select__option.is-active {
    background: var(--color-surface-2);
    color: var(--color-amber-bright);
  }

  @media (pointer: coarse) {
    .hud-select__trigger {
      min-height: 2.75rem;
    }

    .hud-select__option {
      min-height: 2.75rem;
      display: flex;
      align-items: center;
    }
  }
</style>
