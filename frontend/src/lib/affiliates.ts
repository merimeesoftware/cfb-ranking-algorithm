/** Affiliate / geo helpers for model-vs-market CTAs. Rankings stay free. */

export type BookId = 'draftkings' | 'fanduel' | 'betmgm';

export interface AffiliateBook {
	id: BookId;
	name: string;
	/** Placeholder deep links — replace with real affiliate IDs in production secrets. */
	url: string;
	/** US states where this book is commonly available (approx; always verify). */
	states: string[];
}

export const AFFILIATE_DISCLOSURE =
	'We may earn a commission when you open a sportsbook via links on this page. Rankings and TR+ numbers are always free.';

export const RG_HELP_URL = 'https://www.ncpgambling.org/help-treatment/';
export const RG_HELP_LABEL = '1-800-GAMBLER';

/** Approximate legal sports-betting states for client geo hints (not legal advice). */
export const BETTING_ALLOWED_STATES = new Set([
	'AZ', 'CO', 'CT', 'DC', 'IL', 'IN', 'IA', 'KS', 'KY', 'LA', 'MA', 'MD', 'ME', 'MI', 'NC', 'NJ', 'NY',
	'OH', 'OR', 'PA', 'TN', 'VA', 'VT', 'WV', 'WY',
]);

export const BOOKS: AffiliateBook[] = [
	{
		id: 'draftkings',
		name: 'DraftKings',
		url: 'https://sportsbook.draftkings.com/sportsbooks',
		states: ['AZ', 'CO', 'CT', 'IL', 'IN', 'IA', 'KS', 'KY', 'LA', 'MA', 'MD', 'MI', 'NJ', 'NY', 'OH', 'OR', 'PA', 'TN', 'VA', 'VT', 'WV', 'WY'],
	},
	{
		id: 'fanduel',
		name: 'FanDuel',
		url: 'https://sportsbook.fanduel.com/',
		states: ['AZ', 'CO', 'CT', 'DC', 'IL', 'IN', 'IA', 'KS', 'KY', 'LA', 'MA', 'MD', 'MI', 'NJ', 'NY', 'OH', 'PA', 'TN', 'VA', 'WV', 'WY'],
	},
	{
		id: 'betmgm',
		name: 'BetMGM',
		url: 'https://sports.betmgm.com/',
		states: ['AZ', 'CO', 'DC', 'IL', 'IN', 'IA', 'KS', 'KY', 'LA', 'MA', 'MD', 'MI', 'NJ', 'NY', 'OH', 'PA', 'TN', 'VA', 'WV', 'WY'],
	},
];

export function booksForState(state: string | null): AffiliateBook[] {
	if (!state) return BOOKS;
	const st = state.toUpperCase();
	if (!BETTING_ALLOWED_STATES.has(st)) return [];
	return BOOKS.filter((b) => b.states.includes(st));
}

export function detectUsState(): string | null {
	if (typeof window === 'undefined') return null;
	try {
		const stored = localStorage.getItem('tr_us_state');
		if (stored && /^[A-Z]{2}$/.test(stored)) return stored;
	} catch {
		/* ignore */
	}
	return null;
}

export function persistUsState(state: string) {
	try {
		localStorage.setItem('tr_us_state', state.toUpperCase());
	} catch {
		/* ignore */
	}
}
