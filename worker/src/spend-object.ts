import { consumeDaily, resolveDailyLimit, DEFAULT_AI_MAX_CALLS_PER_DAY, DEFAULT_CFBD_MAX_CALLS_PER_DAY, type SpendBucket } from './budget.ts';

interface SpendEnv {
	AI_MAX_CALLS?: string;
	CFBD_MAX_CALLS?: string;
}

/**
 * One global counter for every container. Storage keys are `ai:YYYY-MM-DD`
 * and `cfbd:YYYY-MM-DD` in UTC.
 */
export class SpendBudget implements DurableObject {
	constructor(private readonly state: DurableObjectState, private readonly env: SpendEnv) {}

	async fetch(request: Request): Promise<Response> {
		let payload: { bucket?: string; limit?: number } = {};
		try {
			payload = (await request.json()) as { bucket?: string; limit?: number };
		} catch {
			return Response.json({ ok: false, error: 'json' }, { status: 400 });
		}
		const bucket: SpendBucket | null = payload.bucket === 'ai' || payload.bucket === 'cfbd'
			? payload.bucket
			: null;
		if (!bucket) {
			return Response.json({ ok: false, error: 'bucket' }, { status: 400 });
		}
		const fallback = bucket === 'ai' ? DEFAULT_AI_MAX_CALLS_PER_DAY : DEFAULT_CFBD_MAX_CALLS_PER_DAY;
		const envLimit = bucket === 'ai' ? this.env.AI_MAX_CALLS : this.env.CFBD_MAX_CALLS;
		const limit = resolveDailyLimit(payload.limit ?? envLimit, fallback);
		const store = {
			get: (key: string) => this.state.storage.get<number>(key),
			put: (key: string, value: number) => this.state.storage.put(key, value),
		};
		const result = await this.state.blockConcurrencyWhile(() => consumeDaily(store, bucket, limit));
		return Response.json(result, {
			status: result.ok ? 200 : 429,
			headers: { 'cache-control': 'no-store' },
		});
	}
}
