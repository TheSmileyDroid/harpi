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

<div class="max-w-4xl mx-auto space-y-8">
    <div class="border-b-2 border-retro-primary pb-2 mb-6">
        <h1 class="text-4xl font-bold">DASHBOARD // OVERVIEW</h1>
    </div>

    {#if statsQuery.isLoading}
        <div class="crt-flicker">LOADING DATA STREAMS...</div>
    {:else if statsQuery.isError}
        <div class="text-red-500 crt-flicker">
            ERROR: CONNECTION TO MAINFRAME FAILED.
        </div>
    {:else if stats}
        <div class="grid grid-cols-1 md:grid-cols-2 gap-8">
            <!-- CPU Section -->
            <div class="retro-border p-6 bg-black/30">
                <h2 class="text-2xl mb-4 border-b border-retro-dim pb-1">CPU STATUS</h2>
                <div class="text-6xl font-bold mb-2">{stats.cpu}%</div>
                <div class="w-full bg-retro-off h-4">
                    <div class="bg-retro-primary h-full transition-all duration-500" style="width: {stats.cpu}%"></div>
                </div>
                <div class="mt-2 text-sm text-retro-dim">LOAD AVERAGE</div>
            </div>

            <!-- Memory Section -->
            <div class="retro-border p-6 bg-black/30">
                <h2 class="text-2xl mb-4 border-b border-retro-dim pb-1">MEMORY FRAME</h2>
                <div class="flex justify-between items-end mb-2">
                    <span class="text-4xl font-bold">{stats.memory?.percent}%</span>
                    <span class="text-retro-dim">{(stats.memory?.used / 1024 / 1024 / 1024).toFixed(2)} GB USED</span>
                </div>
                <div class="w-full bg-retro-off h-4">
                    <div class="bg-retro-primary h-full transition-all duration-500" style="width: {stats.memory?.percent}%"></div>
                </div>
                <div class="mt-2 text-sm text-retro-dim">
                    TOTAL: {(stats.memory?.total / 1024 / 1024 / 1024).toFixed(2)} GB
                </div>
            </div>
        </div>
    {/if}
</div>
