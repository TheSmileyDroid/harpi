<script lang="ts">
	import './layout.css';
	import favicon from '$lib/assets/favicon.svg';
	import { QueryClient, QueryClientProvider } from '@tanstack/svelte-query';
	import { browser } from '$app/environment';
	import Header from './components/Header.svelte';

	let { children } = $props();

	const queryClient = new QueryClient({
		defaultOptions: {
			queries: {
				enabled: browser
			}
		}
	});
</script>

<svelte:head>
	<link rel="icon" href={favicon} />
	<title>Harpi // Control System</title>
</svelte:head>

<QueryClientProvider client={queryClient}>
	<div class="crt relative flex min-h-screen w-full flex-col gap-4 p-4">
		<!-- Top Bar -->
		<Header />

		<!-- Main Content -->
		<main class="relative z-10 grow">
			{@render children()}
		</main>

		<!-- Footer -->
		<footer class="z-10 py-2 text-center text-sm text-retro-dim">
			// HARPIPAD CONNECTION ESTABLISHED //
		</footer>
	</div>
</QueryClientProvider>
