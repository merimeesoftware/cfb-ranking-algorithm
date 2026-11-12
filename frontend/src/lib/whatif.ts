/**
 * Browser what-if on the three stored scores. The link is whatif=L-R-C-H.
 * Each token is an integer 0-100, the four add to 100, and Heat is exactly 0.
 * A bad link leaves the official order and returns a notice. Nothing is
 * renormalized. The result is not a week board: it is never cached and it
 * carries no algo stamp. Momentum is not a term. This does not recompute Elo.
 */

export const WHATIF_NOTICE =
	'That what-if link is not used. The official board is unchanged.';

/** Canonical integer token, no sign and no leading zero. */
const CANONICAL_INTEGER = /^(?:0|[1-9]\d*)$/;

export type WhatIfWeights = {
	look: number;
	resume: number;
	league: number;
	heat: 0;
};

export type WhatIfReason = 'missing' | 'extra' | 'non-integer' | 'out-of-range' | 'sum' | 'heat';

export type WhatIfParts = {
	team_name: string;
	team_quality_score: number;
	record_score: number;
	conference_quality_score: number;
	/** Stored on the week file. Never multiplied into the what-if score. */
	momentum?: number | null;
	final_ranking_score?: number;
};

export type WhatIfParse =
	| { ok: true; weights: WhatIfWeights; notice: null; reason: null }
	| { ok: false; weights: null; notice: string; reason: WhatIfReason };

export type WhatIfBoard = {
	ok: boolean;
	weights: WhatIfWeights | null;
	notice: string | null;
	reason: WhatIfReason | null;
	names: readonly string[];
	scores: readonly number[];
	/** Indexes into the official rows. Equal scores keep the earlier index. */
	indexes: readonly number[];
	/** A slider board is not the official week board. */
	official: false;
	/** A slider board is not written to the rankings cache. */
	cached: false;
	/** A slider board must not carry an algo stamp. */
	algo: null;
};

export const OFFICIAL_WEIGHTS: WhatIfWeights = {
	look: 100,
	resume: 0,
	league: 0,
	heat: 0,
};

function finite(value: unknown): number {
	const number = typeof value === 'number' ? value : Number(value);
	return Number.isFinite(number) ? number : 0;
}

function fail(reason: WhatIfReason): WhatIfParse {
	return { ok: false, weights: null, notice: WHATIF_NOTICE, reason };
}

function seal(board: WhatIfBoard): WhatIfBoard {
	if (board.weights) Object.freeze(board.weights);
	Object.freeze(board.names);
	Object.freeze(board.scores);
	Object.freeze(board.indexes);
	return Object.freeze(board);
}

/**
 * Omitted means the official 100-0-0-0 weights. A present value that is
 * missing a token, has an extra token, is not a canonical integer, is
 * outside 0-100, does not add to 100, or has Heat other than 0 is rejected.
 */
export function parseWhatIf(raw: string | null | undefined): WhatIfParse {
	if (raw == null) {
		return { ok: true, weights: { ...OFFICIAL_WEIGHTS }, notice: null, reason: null };
	}
	if (raw === '') return fail('missing');
	const parts = raw.split('-');
	if (parts.length > 4) return fail('extra');
	if (parts.length < 4) return fail('missing');
	const numbers: number[] = [];
	for (const part of parts) {
		if (!CANONICAL_INTEGER.test(part)) return fail('non-integer');
		const value = Number(part);
		if (value > 100) return fail('out-of-range');
		numbers.push(value);
	}
	const look = numbers[0] ?? 0;
	const resume = numbers[1] ?? 0;
	const league = numbers[2] ?? 0;
	const heat = numbers[3] ?? 0;
	if (heat !== 0) return fail('heat');
	if (look + resume + league + heat !== 100) return fail('sum');
	return {
		ok: true,
		weights: { look, resume, league, heat: 0 },
		notice: null,
		reason: null,
	};
}

/** Raw weighted sum. Heat is locked at 0 and is not a term. */
export function whatIfScore(row: WhatIfParts, weights: WhatIfWeights): number {
	if (weights.heat !== 0) {
		throw new Error('Heat weight is locked at 0.');
	}
	return (
		(weights.look / 100) * finite(row.team_quality_score) +
		(weights.resume / 100) * finite(row.record_score) +
		(weights.league / 100) * finite(row.conference_quality_score)
	);
}

/**
 * Stable order: a higher score comes first, and equal scores keep the
 * official order (the same tie-break as order.ts). Does not mutate `rows`.
 * A rejected link returns that official order and a notice.
 */
export function orderWhatIf(
	rows: readonly WhatIfParts[],
	raw: string | null | undefined
): WhatIfBoard {
	const officialNames = rows.map((row) => row.team_name);
	const parsed = parseWhatIf(raw);
	if (!parsed.ok) {
		return seal({
			ok: false,
			weights: null,
			notice: parsed.notice,
			reason: parsed.reason,
			names: officialNames,
			scores: rows.map((row) => finite(row.team_quality_score)),
			indexes: rows.map((_, index) => index),
			official: false,
			cached: false,
			algo: null,
		});
	}
	const ranked = rows.map((row, index) => ({
		name: row.team_name,
		index,
		score: whatIfScore(row, parsed.weights),
	}));
	ranked.sort((a, b) => {
		const byScore = b.score - a.score;
		if (byScore !== 0) return byScore;
		return a.index - b.index;
	});
	return seal({
		ok: true,
		weights: parsed.weights,
		notice: null,
		reason: null,
		names: ranked.map((row) => row.name),
		scores: ranked.map((row) => row.score),
		indexes: ranked.map((row) => row.index),
		official: false,
		cached: false,
		algo: null,
	});
}
