import adapter from '@sveltejs/adapter-static';
import { sveltekit } from '@sveltejs/kit/vite';
import { vitePreprocess } from '@sveltejs/vite-plugin-svelte';
import tailwindcss from '@tailwindcss/vite';
import { defineConfig } from 'vite';

// Docker Compose sets API_PROXY_TARGET=http://api:8080; local host uses Flask :5001
const apiProxyTarget = process.env.API_PROXY_TARGET || 'http://localhost:5001';

export default defineConfig({
	// PUBLIC_ is inlined into the client bundle. Only public settings belong
	// there (PUBLIC_SITE_URL). A key, token, or password must not use this prefix.
	envPrefix: ['VITE_', 'PUBLIC_'],
	plugins: [
		tailwindcss(),
		sveltekit({
			preprocess: vitePreprocess(),
			adapter: adapter({
				pages: 'build',
				assets: 'build',
				fallback: 'index.html', // SPA fallback for client-side routing
				precompress: false,
				strict: true
			}),
			alias: {
				$lib: './src/lib',
				$components: './src/lib/components',
				$stores: './src/lib/stores',
				$utils: './src/lib/utils'
			},
			prerender: {
				handleHttpError: ({ path, message }) => {
					// Ignore missing static assets
					if (path.endsWith('.png') || path.endsWith('.ico')) {
						console.warn(`Missing static asset: ${path}`);
						return;
					}
					throw new Error(message);
				}
			}
		})
	],
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
