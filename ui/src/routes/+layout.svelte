<script lang="ts">
	import './layout.css';
	import favicon from '$lib/assets/favicon.svg';
    import { QueryClient, QueryClientProvider } from '@tanstack/svelte-query'
    import { browser } from '$app/environment'
	import Header from './Header.svelte';

	let { children } = $props();

    const queryClient = new QueryClient({
        defaultOptions: {
            queries: {
                enabled: browser,
            },
        },
    })

</script>

<svelte:head>
    <link rel="icon" href={favicon} />
    <title>Harpi // Control System</title>
</svelte:head>

<QueryClientProvider client={queryClient}>
    <div class="crt min-h-screen w-full relative p-4 flex flex-col gap-4">
        <!-- Top Bar -->
        <Header />

        <!-- Main Content -->
        <main class="flex-grow z-10 relative">
            {@render children()}
        </main>

        <!-- Footer -->
        <footer class="text-center text-retro-dim text-sm py-2 z-10">
            // HARPIPAD CONNECTION ESTABLISHED //
        </footer>
    </div>
</QueryClientProvider>
