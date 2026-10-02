<script>
  let { open = false, message = "", onconfirm, oncancel } = $props();
  let dialog = $state(null);

  $effect(() => {
    if (!dialog) return;
    if (open && !dialog.open) dialog.showModal();
    if (!open && dialog.open) dialog.close();
  });
</script>

<dialog
  class="hud-panel hud-dialog"
  data-testid="confirm-dialog"
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
      data-testid="confirm-cancel"
    >
      Cancel
    </button>
    <button
      type="button"
      class="hud-btn hud-btn-danger"
      onclick={onconfirm}
      data-testid="confirm-execute"
    >
      Confirm
    </button>
  </div>
</dialog>
