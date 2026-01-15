<script lang="ts">
	import { resolve } from '$app/paths';
	import { guildStore, type ChannelsDict, type Guild } from '$lib/stores/guild.svelte';
	import { createMutation, createQuery, useQueryClient } from '@tanstack/svelte-query';

	const queryClient = useQueryClient();

	const guildsQuery = createQuery<Guild[]>(() => ({
		queryKey: ['guilds'],
		queryFn: async () => {
			const res = await fetch('/api/guilds');
			if (!res.ok) throw new Error('Failed to fetch guilds');
			return res.json();
		}
	}));

	const channelsQuery = createQuery<ChannelsDict>(() => ({
		queryKey: ['channels', guildStore.current?.id],
		queryFn: async () => {
			if (!guildStore.current) return { channels: [], current_channel: null };
			const res = await fetch(`/api/guilds/${guildStore.current.id}/channels`);
			if (!res.ok) throw new Error('Failed to fetch channels');
			return res.json();
		},
		enabled: !!guildStore.current
	}));

	const selectChannelMutation = createMutation(() => ({
		mutationFn: async (channelId: string) => {
			if (!guildStore.current) return;
			const res = await fetch(`/api/guilds/${guildStore.current.id}/select-channel`, {
				method: 'POST',
				headers: {
					'Content-Type': 'application/json'
				},
				body: JSON.stringify({ channelId })
			});
			if (!res.ok) throw new Error('Failed to select channel');
			return res.json();
		},
		onSuccess: () => {
			queryClient.invalidateQueries({ queryKey: ['channels'] });
		}
	}));

	function selectGuild(guild: Guild) {
		guildStore.select(guild);
	}
</script>

<header class="retro-border z-10 flex flex-wrap items-center justify-between gap-4 bg-retro-bg p-4">
	<div class="retro-shadow text-2xl font-bold tracking-widest">
		<a href={resolve('/')}>HARPI.OS v2.0</a>
	</div>

	<!-- Guild Selector -->
	<div class="flex items-center gap-2">
		<span class="text-sm text-retro-dim">GUILD:</span>
		<select
			class="cursor-pointer border border-retro-primary bg-retro-bg px-3 py-1 text-lg font-bold text-retro-primary"
			onchange={(e: Event) => {
				const target = e.target as HTMLSelectElement;
				const guild = guildsQuery.data?.find((g) => g.id === target.value);
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

		<select
			class="cursor-pointer border border-retro-primary bg-retro-bg px-3 py-1 text-lg font-bold text-retro-primary"
			disabled={!guildStore.current || !channelsQuery.data}
			onchange={(e: Event) => {
				const target = e.target as HTMLSelectElement;
				const channelId = target.value;
				selectChannelMutation.mutate(channelId);
			}}
		>
			{#if !guildStore.current}
				<option value="">-- SELECT GUILD FIRST --</option>
			{:else if channelsQuery.isLoading}
				<option value="">LOADING...</option>
			{:else if channelsQuery.data}
				{#if !channelsQuery.data.current_channel}
					<option value="">-- SELECT -- </option>
				{/if}
				{#each channelsQuery.data.channels as channel (channel.id)}
					<option value={channel.id} selected={channelsQuery.data.current_channel === channel.id}>
						{channel.name}
					</option>
				{/each}
			{/if}
		</select>
	</div>

	<nav class="flex gap-6 text-xl">
		<a href={resolve('/')} class="hover:underline">[ HOME ]</a>
		<a href={resolve('/music')} class="hover:underline">[ MUSIC ]</a>
	</nav>
	<div class="text-retro-dim">
		{guildStore.current ? `CONNECTED: ${guildStore.current.name.toUpperCase()}` : 'NO GUILD'}
	</div>
</header>
