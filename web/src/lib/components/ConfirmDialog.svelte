<script>
  let {
    open = false,
    message = "",
    onconfirm,
    oncancel,
    testid = "confirm-dialog",
    cancelTestid = "confirm-cancel",
    executeTestid = "confirm-execute",
  } = $props();
  let dialog = $state(null);

  $effect(() => {
    if (!dialog) return;
    if (open && !dialog.open) dialog.showModal();
    if (!open && dialog.open) dialog.close();
  });
</script>

<dialog
  class="hud-panel hud-dialog"
  data-testid={testid}
  bind:this={dialog}
  {oncancel}
  onclose={oncancel}
>
  <p class="confirm-text" data-testid="confirm-text">{message}</p>
  <div class="action-strip">
    <button
      type="button"
      class="hud-btn"
      onclick={oncancel}
      data-testid={cancelTestid}
    >
      Cancel
    </button>
    <button
      type="button"
      class="hud-btn hud-btn-danger"
      onclick={onconfirm}
      data-testid={executeTestid}
    >
      Confirm
    </button>
  </div>
</dialog>
