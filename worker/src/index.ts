import { Container, getRandom } from '@cloudflare/containers';

export interface Env {
	ASSETS: Fetcher;
	CFB_API: DurableObjectNamespace<CfbApiContainer>;
	CFBD_API_KEY?: string;
	MINIMAX_API_KEY?: string;
	CACHE_CLEAR_SECRET?: string;
	CORS_ORIGINS?: string;
	AI_MODE?: string;
	CFBD_OFFLINE?: string;
}

/** Flask API container (gunicorn on port 8080). */
export class CfbApiContainer extends Container<Env> {
	defaultPort = 8080;
	sleepAfter = '30m';

	envVars: Record<string, string> = {
		PORT: '8080',
		FLASK_ENV: 'production',
		CACHE_BACKEND: 'file',
		CACHE_DIR: '/tmp/cfb-cache',
		AI_MODE: 'live',
		CFBD_OFFLINE: '0',
	};

	private runtimeEnvVars(): Record<string, string> {
		return {
			...this.envVars,
			AI_MODE: this.env.AI_MODE ?? this.envVars.AI_MODE,
			CFBD_OFFLINE: this.env.CFBD_OFFLINE ?? this.envVars.CFBD_OFFLINE,
			...(this.env.CFBD_API_KEY ? { CFBD_API_KEY: this.env.CFBD_API_KEY } : {}),
			...(this.env.MINIMAX_API_KEY ? { MINIMAX_API_KEY: this.env.MINIMAX_API_KEY } : {}),
			...(this.env.CACHE_CLEAR_SECRET
				? { CACHE_CLEAR_SECRET: this.env.CACHE_CLEAR_SECRET }
				: {}),
			...(this.env.CORS_ORIGINS ? { CORS_ORIGINS: this.env.CORS_ORIGINS } : {}),
		};
	}

	override async fetch(request: Request): Promise<Response> {
		await this.startAndWaitForPorts({
			startOptions: { envVars: this.runtimeEnvVars() },
			cancellationOptions: { portReadyTimeoutMS: 120_000 },
		});
		return super.fetch(request);
	}
}

/** Invoked for /api/* only (see wrangler.toml run_worker_first). */
export default {
	async fetch(request: Request, env: Env): Promise<Response> {
		const incoming = new URL(request.url);
		const target = new URL(incoming.pathname.replace(/^\/api/, '') || '/', incoming.origin);
		target.search = incoming.search;

		const headers = new Headers(request.headers);
		headers.delete('host');

		const apiRequest = new Request(target.toString(), {
			method: request.method,
			headers,
			body: request.body,
			redirect: 'manual',
		});

		const container = await getRandom(env.CFB_API, 3);
		return container.fetch(apiRequest);
	},
};
