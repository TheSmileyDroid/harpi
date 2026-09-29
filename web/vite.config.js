import { sveltekit } from '@sveltejs/kit/vite';
import { defineConfig } from 'vite';

const port = Number(process.env.VITE_PORT ?? 5173);
const apiTarget = process.env.API_TARGET ?? 'http://localhost:8000';

export default defineConfig({
  plugins: [sveltekit()],
  server: {
    port,
    proxy: {
      '/api': apiTarget
    }
  }
});
