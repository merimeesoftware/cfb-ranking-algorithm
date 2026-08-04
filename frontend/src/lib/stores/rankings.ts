import { writable, derived, get } from 'svelte/store';
import type { Team, Conference, FilterState } from '$lib/types';
import {
	fetchRankingsFromApi,
	fetchAvailableWeeks,
} from '$lib/api';

function getCurrentSeasonWeek(): { year: number; week: number } {
	const now = new Date();
	let year = now.getFullYear();
	const month = now.getMonth() + 1;

	if (month < 8) {
		return { year: year - 1, week: 15 };
	}

	const seasonStart = new Date(year, 7, 24);
	if (now < seasonStart) {
		return { year, week: 1 };
	}

	const delta = now.getTime() - seasonStart.getTime();
	const daysSinceStart = Math.floor(delta / (1000 * 60 * 60 * 24));
	let weekNum = Math.floor(daysSinceStart / 7) + 1;
	if (weekNum > 15) weekNum = 15;
	return { year, week: weekNum };
}

const currentSeasonWeek = getCurrentSeasonWeek();

// Client-side SWR cache keyed by year-week-view
const rankingsCache = new Map<string, { teams: Team[]; conferences: Conference[]; fetchedAt: number }>();
const CACHE_TTL_MS = 5 * 60 * 1000;

function cacheKey(year: number, week: number, view: FilterState['view']): string {
	return `${year}-${week}-${view}`;
}

export const teams = writable<Team[]>([]);
export const conferences = writable<Conference[]>([]);
export const loading = writable<boolean>(false);
export const error = writable<string | null>(null);

export const filterState = writable<FilterState>({
	year: currentSeasonWeek.year,
	week: currentSeasonWeek.week,
	conferenceFilter: null,
	searchQuery: '',
	view: 'fbs',
});

export const availableYears = writable<number[]>(
	Array.from({ length: 5 }, (_, i) => new Date().getFullYear() - i)
);

export const maxWeek = writable<number>(15);

export const filteredTeams = derived(
	[teams, filterState],
	([$teams, $filterState]) => {
		let result = [...$teams];
		if ($filterState.view === 'p4') {
			result = result.filter((t) => t.conference_type === 'Power 4');
		} else if ($filterState.view === 'g5') {
			result = result.filter((t) => t.conference_type === 'Group of 5');
		} else if ($filterState.view === 'fcs') {
			result = result.filter((t) => t.conference_type === 'FCS');
		}
		if ($filterState.conferenceFilter) {
			result = result.filter((t) => t.conference === $filterState.conferenceFilter);
		}
		if ($filterState.searchQuery) {
			const query = $filterState.searchQuery.toLowerCase();
			result = result.filter(
				(t) =>
					t.team_name.toLowerCase().includes(query) ||
					t.conference.toLowerCase().includes(query)
			);
		}
		return result;
	}
);

export const filteredConferences = derived(
	[conferences, filterState],
	([$conferences, $filterState]) => {
		let result = [...$conferences];
		if ($filterState.view === 'p4') {
			result = result.filter((c) => c.conference_type === 'Power 4');
		} else if ($filterState.view === 'g5') {
			result = result.filter((c) => c.conference_type === 'Group of 5');
		} else if ($filterState.view === 'fcs') {
			result = result.filter((c) => c.conference_type === 'FCS');
		}
		return result;
	}
);

export async function loadAvailableWeeks(year: number): Promise<void> {
	const weeks = await fetchAvailableWeeks(year);
	maxWeek.set(Math.max(...weeks, 1));
}

export async function fetchRankings(
	year: number,
	week: number,
	options: { force?: boolean; view?: FilterState['view'] } = {}
): Promise<void> {
	const view = options.view ?? get(filterState).view;
	const key = cacheKey(year, week, view);
	const cached = rankingsCache.get(key);

	if (cached && !options.force && Date.now() - cached.fetchedAt < CACHE_TTL_MS) {
		teams.set(cached.teams);
		conferences.set(cached.conferences);
		filterState.update((state) => ({ ...state, year, week }));
		return;
	}

	loading.set(true);
	error.set(null);

	try {
		const data = await fetchRankingsFromApi(year, week, view);
		teams.set(data.teams);
		conferences.set(data.conferences);
		rankingsCache.set(key, {
			teams: data.teams,
			conferences: data.conferences,
			fetchedAt: Date.now(),
		});
		filterState.update((state) => ({ ...state, year: data.year, week: data.week ?? week }));
	} catch (e) {
		const message = e instanceof Error ? e.message : 'Failed to fetch rankings';
		error.set(message);
		if (cached) {
			teams.set(cached.teams);
			conferences.set(cached.conferences);
		} else {
			teams.set([]);
			conferences.set([]);
		}
	} finally {
		loading.set(false);
	}
}

export function setView(view: 'fbs' | 'p4' | 'g5' | 'fcs'): void {
	filterState.update((state) => ({ ...state, view, conferenceFilter: null }));
}

export function setYear(year: number): void {
	filterState.update((state) => ({ ...state, year }));
	loadAvailableWeeks(year);
}

export function setWeek(week: number): void {
	filterState.update((state) => ({ ...state, week }));
}

export function setConferenceFilter(conference: string | null): void {
	filterState.update((state) => ({ ...state, conferenceFilter: conference }));
}

export function setSearchQuery(query: string): void {
	filterState.update((state) => ({ ...state, searchQuery: query }));
}

export function clearFilters(): void {
	filterState.update((state) => ({ ...state, conferenceFilter: null, searchQuery: '' }));
}

export function parseUrlParams(search: string): Partial<FilterState> & { tab?: 'teams' | 'conferences'; team?: string } {
	const params = new URLSearchParams(search);
	const result: Partial<FilterState> & { tab?: 'teams' | 'conferences'; team?: string } = {};
	const year = params.get('year');
	const week = params.get('week');
	const view = params.get('view');
	const tab = params.get('tab');
	const team = params.get('team');
	const q = params.get('q');
	const conf = params.get('conference');
	if (year) result.year = parseInt(year, 10);
	if (week) result.week = parseInt(week, 10);
	if (view && ['fbs', 'p4', 'g5', 'fcs'].includes(view)) {
		result.view = view as FilterState['view'];
	}
	if (tab === 'teams' || tab === 'conferences') result.tab = tab;
	if (team) result.team = team;
	if (q) result.searchQuery = q;
	if (conf) result.conferenceFilter = conf;
	return result;
}

export function buildUrlParams(
	state: FilterState,
	tab: 'teams' | 'conferences',
	teamName?: string | null
): string {
	const params = new URLSearchParams();
	params.set('year', String(state.year));
	params.set('week', String(state.week));
	params.set('view', state.view);
	params.set('tab', tab);
	if (state.searchQuery) params.set('q', state.searchQuery);
	if (state.conferenceFilter) params.set('conference', state.conferenceFilter);
	if (teamName) params.set('team', teamName);
	return params.toString();
}
