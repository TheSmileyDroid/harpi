import path from 'path';
import reactScan from '@react-scan/vite-plugin-react-scan';
import { TanStackRouterVite } from '@tanstack/router-plugin/vite';
import react from '@vitejs/plugin-react-swc';
import ReactCompiler from 'babel-plugin-react-compiler';
import { defineConfig } from 'vite';

// https://vite.dev/config/
export default defineConfig({
  plugins: [
    TanStackRouterVite({ target: 'react', autoCodeSplitting: true }),
    react({
      //@ts-expect-error Babel
      babel: {
        plugins: [ReactCompiler],
      },
    }),
    reactScan({
      autoDisplayNames: true,
      // options (optional)
    }),
  ],
  resolve: {
    alias: {
      '@': path.resolve(__dirname, './src'),
    },
  },
  define: {
    'process.env': {},
  },
});
