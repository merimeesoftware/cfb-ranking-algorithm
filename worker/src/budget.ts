/**
 * Global per-UTC-day paid-call budget.
 *
 * Unset configuration uses these defaults. An unset variable is never unlimited.
 * xAI and Workers AI default to 0 so a live prompt is refused until a cap is set.
 * The named container instance `spend-budget` is the shared counter. Flask
 * keeps a same-number per-process cap as a second gate.
 */
export const DEFAULT_XAI_MAX_CALLS_PER_DAY = 0;
export const DEFAULT_WORKERS_AI_MAX_CALLS_PER_DAY = 0;
export const DEFAULT_CFBD_MAX_CALLS_PER_DAY = 25;

export type SpendBucket = 'xai' | 'workers_ai' | 'cfbd';

export interface BudgetEnv {
	XAI_MAX_CALLS?: string;
	WORKERS_AI_MAX_CALLS?: string;
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
	code?: string;
}

const FALLBACKS: Record<SpendBucket, number> = {
	xai: DEFAULT_XAI_MAX_CALLS_PER_DAY,
	workers_ai: DEFAULT_WORKERS_AI_MAX_CALLS_PER_DAY,
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
	const raw = bucket === 'xai'
		? env.XAI_MAX_CALLS
		: bucket === 'workers_ai'
			? env.WORKERS_AI_MAX_CALLS
			: env.CFBD_MAX_CALLS;
	return resolveDailyLimit(raw, FALLBACKS[bucket]);
}

export function budgetKey(bucket: SpendBucket, now: Date = new Date()): string {
	return `${bucket}:${utcDay(now)}`;
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
): Promise<ConsumeResult> {
	const day = utcDay(now);
	const key = `${bucket}:${day}`;
	const current = (await store.get(key)) ?? 0;
	if (current >= limit) {
		return { ok: false, count: current, limit, day, bucket, code: `${bucket}_budget` };
	}
	const next = current + 1;
	await store.put(key, next);
	return { ok: true, count: next, limit, day, bucket };
}
