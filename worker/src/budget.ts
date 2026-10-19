/**
 * Global per-UTC-day paid-call budget.
 *
 * Unset configuration uses these defaults. An unset variable is never unlimited.
 * The Durable Object is the shared counter across container instances. Flask
 * keeps a same-number per-process cap as a second gate.
 */
export const DEFAULT_AI_MAX_CALLS_PER_DAY = 100;
export const DEFAULT_CFBD_MAX_CALLS_PER_DAY = 25;

export type SpendBucket = 'ai' | 'cfbd';

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

export function dailyLimitFor(
	bucket: SpendBucket,
	env: { AI_MAX_CALLS?: string; CFBD_MAX_CALLS?: string },
): number {
	if (bucket === 'ai') {
		return resolveDailyLimit(env.AI_MAX_CALLS, DEFAULT_AI_MAX_CALLS_PER_DAY);
	}
	return resolveDailyLimit(env.CFBD_MAX_CALLS, DEFAULT_CFBD_MAX_CALLS_PER_DAY);
}

export function budgetKey(bucket: SpendBucket, now: Date = new Date()): string {
	return `${bucket}:${utcDay(now)}`;
}

/**
 * Increment the day's counter when it is still under the limit.
 * A planted count equal to the limit makes the next call return ok: false.
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
