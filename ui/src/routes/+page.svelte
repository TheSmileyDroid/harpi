<script lang="ts">
	import { createQuery } from '@tanstack/svelte-query';

	type ServerStats = {
		cpu: number;
		memory: {
			total: number;
			available: number;
			percent: number;
			used: number;
			free: number;
		};
	};

	const statsQuery = createQuery<ServerStats>(() => ({
		queryKey: ['serverstatus'],
		queryFn: async () => {
			const res = await fetch('/api/serverstatus');
			if (!res.ok) throw new Error('Failed to fetch stats');
			return res.json();
		},
		refetchInterval: 5000
	}));

	const stats = $derived(statsQuery.data);
</script>

<div class="mx-auto max-w-4xl space-y-8">
	<div class="mb-6 border-b-2 border-retro-primary pb-2">
		<h1 class="text-4xl font-bold">DASHBOARD // OVERVIEW</h1>
	</div>

	{#if statsQuery.isLoading}
		<div class="crt-flicker">LOADING DATA STREAMS...</div>
	{:else if statsQuery.isError}
		<div class="crt-flicker text-red-500">ERROR: CONNECTION TO MAINFRAME FAILED.</div>
	{:else if stats}
		<div class="grid grid-cols-1 gap-8 md:grid-cols-2">
			<!-- CPU Section -->
			<div class="retro-border bg-black/30 p-6">
				<h2 class="mb-4 border-b border-retro-dim pb-1 text-2xl">CPU STATUS</h2>
				<div class="mb-2 text-6xl font-bold">{stats.cpu}%</div>
				<div class="h-4 w-full bg-retro-off">
					<div
						class="h-full bg-retro-primary transition-all duration-500"
						style="width: {stats.cpu}%"
					></div>
				</div>
				<div class="mt-2 text-sm text-retro-dim">LOAD AVERAGE</div>
			</div>

			<!-- Memory Section -->
			<div class="retro-border bg-black/30 p-6">
				<h2 class="mb-4 border-b border-retro-dim pb-1 text-2xl">MEMORY FRAME</h2>
				<div class="mb-2 flex items-end justify-between">
					<span class="text-4xl font-bold">{stats.memory?.percent}%</span>
					<span class="text-retro-dim"
						>{(stats.memory?.used / 1024 / 1024 / 1024).toFixed(2)} GB USED</span
					>
				</div>
				<div class="h-4 w-full bg-retro-off">
					<div
						class="h-full bg-retro-primary transition-all duration-500"
						style="width: {stats.memory?.percent}%"
					></div>
				</div>
				<div class="mt-2 text-sm text-retro-dim">
					TOTAL: {(stats.memory?.total / 1024 / 1024 / 1024).toFixed(2)} GB
				</div>
			</div>
		</div>
	{/if}
</div>
