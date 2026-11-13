/**
 * Display-only slate label. Same floors as ranking_algorithm.soft_slate_flag.
 * Derived from columns already on the v5.5 row, so a board rebuild is not
 * required. This does not change the Elo order. A stored boolean is ignored.
 *
 * soft_win_share uses end-of-week Elo, so a later rating can move a win
 * under the line after the fact.
 */

export const SOFT_SLATE_MIN_DECISIONS = 6;
export const SOFT_SLATE_MIN_WIN_RATE = 0.75;
export const SOFT_SLATE_MIN_SOFT_WIN_SHARE = 0.5;

export interface SoftSlateInput {
	wins?: number;
	losses?: number;
	quality_wins?: number;
	soft_win_share?: number;
}

function isCountable(value: number | undefined): value is number {
	return typeof value === 'number' && Number.isFinite(value);
}

/** True only at the floors above. record_ahead is not an input. */
export function softSlateFlag(row: SoftSlateInput): boolean {
	const wins = row.wins;
	const losses = row.losses;
	const quality = row.quality_wins;
	const share = row.soft_win_share;
	if (!isCountable(wins) || !isCountable(losses) || !isCountable(quality) || !isCountable(share)) {
		return false;
	}
	if (wins < 0 || losses < 0) return false;
	const decisions = wins + losses;
	if (decisions < SOFT_SLATE_MIN_DECISIONS) return false;
	if (wins / decisions < SOFT_SLATE_MIN_WIN_RATE) return false;
	if (quality !== 0) return false;
	return share >= SOFT_SLATE_MIN_SOFT_WIN_SHARE;
}

export function optionalNumber(value: unknown): number | undefined {
	if (typeof value === 'boolean' || value == null) return undefined;
	if (typeof value === 'number') return Number.isFinite(value) ? value : undefined;
	if (typeof value === 'string' && value.trim() !== '') {
		const parsed = Number(value);
		return Number.isFinite(parsed) ? parsed : undefined;
	}
	return undefined;
}

/** Fields for Team. The boolean is derived; raw.soft_slate_flag is not read. */
export function softSlateFromRow(raw: Record<string, unknown>): {
	record_ahead?: number;
	soft_win_share?: number;
	soft_slate_flag: boolean;
} {
	const records =
		raw.records && typeof raw.records === 'object'
			? (raw.records as Record<string, unknown>)
			: {};
	const wins = optionalNumber(records.total_wins ?? raw.wins);
	const losses = optionalNumber(records.total_losses ?? raw.losses);
	const share = optionalNumber(raw.soft_win_share);
	return {
		record_ahead: optionalNumber(raw.record_ahead),
		soft_win_share: share,
		soft_slate_flag: softSlateFlag({
			wins,
			losses,
			quality_wins: optionalNumber(raw.quality_wins),
			soft_win_share: share,
		}),
	};
}
