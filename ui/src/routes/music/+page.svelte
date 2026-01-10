<script lang="ts">
    import { createQuery, createMutation, useQueryClient } from '@tanstack/svelte-query';
    import { guildStore } from '$lib/stores/guild.svelte';

    const queryClient = useQueryClient();

    let connected = $state(false);
    let newMusicLink = $state('');

    type MusicData = {
        current_music: { title: string; duration: string; url: string } | null;
        progress: number;
        queue: { title: string; duration: string; url: string }[];
        is_playing: boolean;
        is_paused: boolean;
    };

    const guildId = $derived(guildStore.current?.id);

    const musicQuery = createQuery<MusicData>(() => ({
        queryKey: ['music', guildId],
        queryFn: async () => {
            if (!guildId) throw new Error('No guild selected');
            const res = await fetch(`/api/music/status?guild_id=${guildId}`);
            if (!res.ok) throw new Error('Failed to fetch status');
            return res.json();
        },
        enabled: !!guildId,
        refetchInterval: 5000
    }));

    const controlMutation = createMutation<void, Error, string>(() => ({
        mutationFn: async (action: string) => {
            if (!guildId) throw new Error('No guild selected');
            await fetch('/api/music/control', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ guild_id: guildId, action })
            });
        },
        onSuccess: () => {
            queryClient.invalidateQueries({ queryKey: ['music', guildId] });
        },
        onError: (error: Error) => {
            console.error("Control failed", error);
        }
    }));

    const addMusicMutation = createMutation<void, Error, string>(() => ({
        mutationFn: async (link: string) => {
            if (!guildId) throw new Error('No guild selected');
            await fetch('/api/music/add', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ guild_id: guildId, link })
            });
        },
        onSuccess: () => {
            newMusicLink = '';
            queryClient.invalidateQueries({ queryKey: ['music', guildId] });
        },
        onError: (error: Error) => {
            console.error("Add music failed", error);
        }
    }));

    const musicData = $derived(musicQuery.data);

    function handleAddMusic(e: SubmitEvent) {
        e.preventDefault();
        if (newMusicLink.trim()) {
            addMusicMutation.mutate(newMusicLink.trim());
        }
    }
</script>

<div class="max-w-4xl mx-auto space-y-8">
    <div class="border-b-2 border-retro-primary pb-2 mb-6 flex justify-between items-end">
        <h1 class="text-4xl font-bold">AUDIO // CONTROL</h1>
        <div class="text-sm text-retro-dim mb-1">
            STATUS: {connected ? 'LINKED' : 'OFFLINE'}
        </div>
    </div>

    {#if !guildId}
        <div class="text-retro-dim text-center py-8 text-xl crt-flicker">
            SELECT A GUILD TO ACCESS AUDIO CONTROLS
        </div>
    {:else if musicQuery.isLoading}
        <div class="crt-flicker">LOADING DATA STREAMS...</div>
    {:else if musicQuery.isError}
        <div class="text-retro-dim text-center py-4">NO ACTIVE AUDIO SESSION</div>
    {:else}
        <!-- Add Music Form -->
        <form onsubmit={handleAddMusic} class="retro-border p-4 bg-black/30 flex gap-4">
            <input
                type="text"
                bind:value={newMusicLink}
                placeholder="ENTER YOUTUBE LINK..."
                class="flex-1 bg-retro-bg border border-retro-primary text-retro-primary px-4 py-2 placeholder:text-retro-dim"
            />
            <button
                type="submit"
                disabled={addMusicMutation.isPending || !newMusicLink.trim()}
                class="px-6 py-2 border-2 border-retro-primary hover:bg-retro-primary hover:text-retro-bg font-bold transition-colors disabled:opacity-50"
            >
                {addMusicMutation.isPending ? 'ADDING...' : '[ ADD ]'}
            </button>
        </form>

        <!-- Now Playing -->
        <div class="retro-border p-6 bg-black/30 relative overflow-hidden">
            <h2 class="text-xl text-retro-dim mb-2">NOW PLAYING sequence...</h2>

            {#if musicData?.current_music}
                <div class="text-3xl font-bold mb-4 retro-shadow truncate">
                    {musicData.current_music.title}
                </div>

                <div class="mb-4">
                    <div class="flex justify-between text-xs mb-1">
                        <span>{musicData.progress}s</span>
                        <span>{musicData.current_music.duration}</span>
                    </div>
                    <div class="w-full bg-retro-off h-6 border border-retro-primary p-1">
                        <div class="bg-retro-primary h-full w-full opacity-50 animate-pulse"></div>
                    </div>
                </div>
            {:else}
                <div class="text-2xl text-retro-dim italic">NO AUDIO SIGNAL DETECTED</div>
            {/if}

            <!-- Controls -->
            <div class="flex gap-4 mt-6 justify-center flex-wrap">
                {#if musicData?.is_paused}
                    <button
                        onclick={() => controlMutation.mutate('resume')}
                        disabled={controlMutation.isPending}
                        class="px-6 py-2 border-2 border-retro-primary hover:bg-retro-primary hover:text-retro-bg font-bold transition-colors disabled:opacity-50">
                        [ RESUME ]
                    </button>
                {:else}
                    <button
                        onclick={() => controlMutation.mutate('pause')}
                        disabled={controlMutation.isPending}
                        class="px-6 py-2 border-2 border-retro-primary hover:bg-retro-primary hover:text-retro-bg font-bold transition-colors disabled:opacity-50">
                        [ PAUSE ]
                    </button>
                {/if}
                <button
                    onclick={() => controlMutation.mutate('stop')}
                    disabled={controlMutation.isPending}
                    class="px-6 py-2 border-2 border-retro-primary hover:bg-retro-primary hover:text-retro-bg font-bold transition-colors disabled:opacity-50">
                    [ STOP ]
                </button>
                <button
                    onclick={() => controlMutation.mutate('skip')}
                    disabled={controlMutation.isPending}
                    class="px-6 py-2 border-2 border-retro-primary hover:bg-retro-primary hover:text-retro-bg font-bold transition-colors disabled:opacity-50">
                    [ SKIP ]
                </button>
            </div>
        </div>

        <!-- Queue -->
        <div class="retro-border p-6 bg-black/30">
            <h2 class="text-xl border-b border-retro-dim pb-2 mb-4">QUEUE SEQUENCE</h2>
            {#if musicData?.queue && musicData.queue.length > 0}
                <ul class="space-y-2">
                    {#each musicData.queue as track, i (track.title + i)}
                        <li class="flex gap-4 items-center">
                            <span class="text-retro-dim w-6">{i + 1}.</span>
                            <span class="truncate flex-1">{track.title}</span>
                            <span class="text-sm text-retro-dim">{track.duration}</span>
                        </li>
                    {/each}
                </ul>
            {:else}
                <div class="text-retro-dim text-center py-4">QUEUE BUFFER EMPTY</div>
            {/if}
        </div>
    {/if}
</div>
