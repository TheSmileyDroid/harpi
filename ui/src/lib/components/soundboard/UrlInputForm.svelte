<script lang="ts">
	interface Props {
		label: string;
		placeholder?: string;
		value: string;
		loading: boolean;
		error: string;
		disabled?: boolean;
		onsubmit: () => void;
		oninput: (value: string) => void;
	}

	let {
		label,
		placeholder = 'youtube url...',
		value,
		loading,
		error,
		disabled = false,
		onsubmit,
		oninput
	}: Props = $props();

	function handleKeydown(e: KeyboardEvent) {
		if (e.key === 'Enter') onsubmit();
	}
</script>

<div class="border border-retro-off bg-black/30 p-3">
	<div class="mb-2 text-xs text-retro-dim">{label}</div>
	<div class="flex gap-1">
		<input
			type="text"
			{value}
			oninput={(e) => oninput((e.target as HTMLInputElement).value)}
			onkeydown={handleKeydown}
			{placeholder}
			disabled={loading || disabled}
			class="flex-1 border border-retro-dim bg-retro-bg px-2 py-1 text-xs text-retro-primary placeholder:text-retro-off disabled:opacity-50"
		/>
		<button
			onclick={onsubmit}
			disabled={loading || !value.trim() || disabled}
			class="border border-retro-primary px-2 py-1 text-xs text-retro-primary transition-colors hover:bg-retro-primary hover:text-retro-bg disabled:opacity-50"
		>
			{loading ? '...' : '[ ADD ]'}
		</button>
	</div>
	{#if error}
		<div class="mt-1 text-xs text-red-500">{error}</div>
	{/if}
</div>
