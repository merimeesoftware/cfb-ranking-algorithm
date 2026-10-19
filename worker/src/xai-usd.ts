/**
 * xAI weekly dollar estimate.
 *
 * Prices: https://docs.x.ai/developers/pricing
 * grok-4 is not listed. grok-4.7 on that page is $2 / $6 per 1M tokens,
 * and $4 / $12 at long context. These rates are a high placeholder marked
 * verify in config/xai-usd.json.
 */
export const XAI_USD = {
	model: 'grok-4',
	price_status: 'verify',
	source_url: 'https://docs.x.ai/developers/pricing',
	usd_per_million_input_tokens: 25,
	usd_per_million_output_tokens: 100,
	max_output_tokens: 256,
	input_tokens_per_char: 1,
	weekly_limit_usd: 5,
};

export function usdToMicros(value: string | number): number {
	const text = String(value).trim();
	if (!/^\d+(\.\d{1,6})?$/.test(text)) return 0;
	const [whole, frac = ''] = text.split('.');
	const padded = (frac + '000000').slice(0, 6);
	return Number(whole) * 1_000_000 + Number(padded);
}

export function weeklyCapMicros(raw: string | undefined): number {
	if (raw === undefined || raw.trim() === '') return 0;
	return usdToMicros(raw);
}

/** UTC ISO week. Rolls at Monday 00:00 UTC. */
export function isoWeekId(now: Date = new Date()): string {
	const tmp = new Date(Date.UTC(now.getUTCFullYear(), now.getUTCMonth(), now.getUTCDate()));
	const day = tmp.getUTCDay() || 7;
	tmp.setUTCDate(tmp.getUTCDate() + 4 - day);
	const yearStart = new Date(Date.UTC(tmp.getUTCFullYear(), 0, 1));
	const week = Math.ceil(((tmp.getTime() - yearStart.getTime()) / 86_400_000 + 1) / 7);
	return `${tmp.getUTCFullYear()}-W${String(week).padStart(2, '0')}`;
}

export function xaiUsdKey(now: Date = new Date()): string {
	return `xai:usd:${isoWeekId(now)}`;
}

export function worstCaseMicros(prompt: string): number {
	const inputTokens = (prompt || '').length * XAI_USD.input_tokens_per_char;
	return (
		inputTokens * XAI_USD.usd_per_million_input_tokens
		+ XAI_USD.max_output_tokens * XAI_USD.usd_per_million_output_tokens
	);
}

export function wouldCross(spentMicros: number, worstMicros: number, capMicros: number): boolean {
	return spentMicros + worstMicros > capMicros;
}
