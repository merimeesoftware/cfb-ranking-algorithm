import { sveltekit } from '@sveltejs/kit/vite';
import { defineConfig } from 'vite';

// Docker Compose sets API_PROXY_TARGET=http://api:8080; local host uses Flask :5001
const apiProxyTarget = process.env.API_PROXY_TARGET || 'http://localhost:5001';

export default defineConfig({
	plugins: [sveltekit()],
	server: {
		// Docker Desktop on Windows often misses bind-mount file events; polling keeps HMR honest.
		watch: {
			usePolling: true,
			interval: 1000
		},
		proxy: {
			'/api': {
				target: apiProxyTarget,
				changeOrigin: true,
				rewrite: (path) => path.replace(/^\/api/, '')
			}
		}
	}
});
