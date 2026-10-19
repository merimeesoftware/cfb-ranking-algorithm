/**
 * Global per-UTC-day paid-call budget.
 *
 * Unset configuration uses these defaults. An unset variable is never unlimited.
 * xAI is a hard 0. XAI_MAX_CALLS cannot raise it. Workers AI uses AI_MAX_CALLS
 * and defaults to 100. The named container instance `spend-budget` is the
 * shared counter. Flask keeps a same-number per-process cap as a second gate.
 *
 * Workers AI neurons (@cf/meta/llama-3.1-8b-instruct-fp8, the closest current
 * id; llama-3.1-8b-instruct-fast is not in the catalog):
 *   13778 per million input tokens, 26128 per million output tokens.
 *   Worst case = ceil((4000*13778 + 160*26128) / 1_000_000) = 60 per call.
 *   AI_MAX_CALLS 100 * 60 = 6000, ceiling 8000, free daily Neurons 10000.
 *   Fin's band for 100 calls is about 500 to 3800. The output cap holds the
 *   published-rate worst case under 8000.
 */
export const DEFAULT_XAI_MAX_CALLS_PER_DAY = 0;
export const DEFAULT_AI_MAX_CALLS_PER_DAY = 100;
export const DEFAULT_CFBD_MAX_CALLS_PER_DAY = 25;

/**
 * CFBD free quota is shared. This app is provider `cfbd`, source `app`.
 * A later source can use the same provider. Source `mcp` is reserved for
 * #115 and is not accepted here.
 */
export const CFBD_PROVIDER = 'cfbd' as const;
export const CFBD_APP_SOURCE = 'app';

export type SpendBucket = 'xai' | 'workers_ai' | 'cfbd';

export interface BudgetEnv {
	XAI_MAX_CALLS?: string;
	AI_MAX_CALLS?: string;
	CFBD_MAX_CALLS?: string;
}

export interface BudgetStore {
	get(key: string): Promise<number | undefined>;
	put(key: string, value: number): Promise<void>;
}

export interface ConsumeResult {
	ok: boolean;
	count: number;
	limit: number;
	day: string;
	bucket: SpendBucket;
	provider: SpendBucket;
	source?: string;
	code?: string;
}

const FALLBACKS: Record<SpendBucket, number> = {
	xai: DEFAULT_XAI_MAX_CALLS_PER_DAY,
	workers_ai: DEFAULT_AI_MAX_CALLS_PER_DAY,
	cfbd: DEFAULT_CFBD_MAX_CALLS_PER_DAY,
};

export function utcDay(now: Date = new Date()): string {
	return now.toISOString().slice(0, 10);
}

/** Missing, blank, or non-integer values fall back to the in-code default. */
export function resolveDailyLimit(raw: unknown, fallback: number): number {
	if (raw === undefined || raw === null) return fallback;
	const text = String(raw).trim();
	if (!text) return fallback;
	if (!/^\d+$/.test(text)) return fallback;
	const parsed = Number(text);
	if (!Number.isInteger(parsed) || parsed < 0) return fallback;
	return parsed;
}

export function dailyLimitFor(bucket: SpendBucket, env: BudgetEnv): number {
	if (bucket === 'xai') return DEFAULT_XAI_MAX_CALLS_PER_DAY;
	const raw = bucket === 'workers_ai' ? env.AI_MAX_CALLS : env.CFBD_MAX_CALLS;
	return resolveDailyLimit(raw, FALLBACKS[bucket]);
}

export function budgetKey(
	bucket: SpendBucket,
	now: Date = new Date(),
	source?: string,
): string {
	const day = utcDay(now);
	if (bucket === CFBD_PROVIDER) return `${CFBD_PROVIDER}:${source || CFBD_APP_SOURCE}:${day}`;
	return `${bucket}:${day}`;
}

/**
 * Increment the day's counter when it is still under the limit.
 * A limit of 0 refuses the first call. A planted count equal to the limit
 * makes the next call return ok: false.
 */
export async function consumeDaily(
	store: BudgetStore,
	bucket: SpendBucket,
	limit: number,
	now: Date = new Date(),
	source?: string,
): Promise<ConsumeResult> {
	const day = utcDay(now);
	const named = bucket === CFBD_PROVIDER ? (source || CFBD_APP_SOURCE) : undefined;
	const key = budgetKey(bucket, now, named);
	const current = (await store.get(key)) ?? 0;
	const base = { limit, day, bucket, provider: bucket, source: named };
	if (current >= limit) {
		return { ok: false, count: current, ...base, code: `${bucket}_budget` };
	}
	const next = current + 1;
	await store.put(key, next);
	return { ok: true, count: next, ...base };
}
