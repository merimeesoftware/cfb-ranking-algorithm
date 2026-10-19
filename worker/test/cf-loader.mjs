import { existsSync } from 'node:fs';
import { fileURLToPath } from 'node:url';

export async function resolve(specifier, context, nextResolve) {
	if (specifier === 'cloudflare:workers') {
		return {
			url: new URL('./cloudflare-workers-stub.mjs', import.meta.url).href,
			shortCircuit: true,
		};
	}
	if (
		specifier.startsWith('.')
		&& context.parentURL
		&& !/\.(?:js|mjs|cjs|ts|json)$/.test(specifier)
	) {
		const candidate = new URL(`${specifier}.js`, context.parentURL);
		if (existsSync(fileURLToPath(candidate))) {
			return { url: candidate.href, shortCircuit: true };
		}
	}
	return nextResolve(specifier, context);
}
