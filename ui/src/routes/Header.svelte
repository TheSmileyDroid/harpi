<script lang="ts">
	import { resolve } from "$app/paths";
	import { guildStore, type Guild } from '$lib/stores/guild.svelte';
	import { createQuery } from '@tanstack/svelte-query';

	const guildsQuery = createQuery<Guild[]>(() => ({
        queryKey: ['guilds'],
        queryFn: async () => {
            const res = await fetch('/api/guilds');
            if (!res.ok) throw new Error('Failed to fetch guilds');
            return res.json();
        }
    }));

    function selectGuild(guild: Guild) {
        guildStore.select(guild);
    }
</script>


<header class="retro-border p-4 flex justify-between items-center bg-retro-bg z-10 flex-wrap gap-4">
    <div class="text-2xl font-bold tracking-widest retro-shadow">
        <a href={resolve('/')}>HARPI.OS v2.0</a>
    </div>

    <!-- Guild Selector -->
    <div class="flex items-center gap-2">
        <span class="text-retro-dim text-sm">GUILD:</span>
        <select
            class="bg-retro-bg border border-retro-primary text-retro-primary px-3 py-1 text-lg font-bold cursor-pointer"
            onchange={(e: Event) => {
                const target = e.target as HTMLSelectElement;
                const guild = guildsQuery.data?.find(g => g.id === target.value);
                if (guild) selectGuild(guild);
            }}
        >
            {#if !guildStore.current}
                <option value="">-- SELECT --</option>
            {/if}
            {#if guildsQuery.data}
                {#each guildsQuery.data as guild (guild.id)}
                    <option value={guild.id} selected={guildStore.current?.id === guild.id}>
                        {guild.name}
                    </option>
                {/each}
            {:else if guildsQuery.isLoading}
                <option value="">LOADING...</option>
            {:else}
                <option value="">NO GUILDS</option>
            {/if}
        </select>
    </div>

    <nav class="flex gap-6 text-xl">
        <a href={resolve("/")} class="hover:underline">[ HOME ]</a>
        <a href={resolve("/music")} class="hover:underline">[ MUSIC ]</a>
    </nav>
    <div class="text-retro-dim">
        {guildStore.current ? `CONNECTED: ${guildStore.current.name.toUpperCase()}` : 'NO GUILD'}
    </div>
</header>
