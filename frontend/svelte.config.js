import adapter from '@sveltejs/adapter-static';
import { vitePreprocess } from '@sveltejs/vite-plugin-svelte';

/** @type {import('@sveltejs/kit').Config} */
const config = {
	preprocess: vitePreprocess(),

	kit: {
		adapter: adapter({
			pages: 'build',
			assets: 'build',
			fallback: 'index.html', // SPA fallback for client-side routing
			precompress: false,
			strict: true
		}),
		alias: {
			$components: './src/lib/components',
			$stores: './src/lib/stores',
			$utils: './src/lib/utils'
		},
		prerender: {
			handleHttpError: ({ path, referrer, message }) => {
				// Ignore missing static assets
				if (path.endsWith('.png') || path.endsWith('.ico')) {
					console.warn(`Missing static asset: ${path}`);
					return;
				}
				throw new Error(message);
			}
		}
	}
};

export default config;
