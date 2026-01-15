import { handleProxy } from 'sveltekit-proxy';
import process from 'process';
import type { Handle } from '@sveltejs/kit';

const apiPath = '/api';

export const handle: Handle = async ({ event, resolve }) => {
	if (event.url.pathname.startsWith(apiPath)) {
		return handleProxy({
			target: process.env.BACKEND_URL || 'http://127.0.0.1:8000',
			onRequest: ({ request }) => {
				// Optionally modify the request before forwarding
				const headers = new Headers(request.headers);
				headers.set('x-proxied-by', 'sveltekit-proxy');
				return new Request(request, { headers });
			},
			onResponse: ({ response, duration }) => {
				// Optionally log response info
				console.log(`[Proxy] ${response.status} in ${duration.toFixed(2)}ms`);
			},
			onError: ({ error, request }) => {
				console.error('[Proxy Error]', error, request.url);
			}
		})({ event, resolve });
	}

	return resolve(event);
};
