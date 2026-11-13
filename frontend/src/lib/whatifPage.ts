/**
 * Week-page what-if data. The official table, Share Top 25, the citation,
 * and JSON-LD stay on Elo and the bare week path. Nothing here is rendered
 * until a later signed control. Nothing here is sent to /api.
 */
import { weekPath } from './brand';
import { orderWhatIf, type WhatIfBoard, type WhatIfParts } from './whatif';

/** Brief example. A signed control will write the integers it actually lands on. */
export const WHATIF_COPY_TOKEN = '70-30-0-0';

export function readWhatIfParam(search: string): string | null | undefined {
	const params = new URLSearchParams(search.startsWith('?') ? search.slice(1) : search);
	if (!params.has('whatif')) return undefined;
	const values = params.getAll('whatif');
	if (values.length !== 1) return '';
	return values[0] ?? '';
}

export function copyWhatIfLink(year: number, week: number): string {
	return `${weekPath(year, week)}?whatif=${WHATIF_COPY_TOKEN}`;
}

export function resetWhatIfSearch(search: string): string {
	const params = new URLSearchParams(search.startsWith('?') ? search.slice(1) : search);
	params.delete('whatif');
	const next = params.toString();
	return next ? `?${next}` : '';
}

export function resetWhatIfLink(year: number, week: number, search = ''): string {
	return `${weekPath(year, week)}${resetWhatIfSearch(search)}`;
}

export function officialSharePath(year: number, week: number): string {
	return weekPath(year, week);
}

export function officialShareNames(official: readonly { team_name: string }[], count = 5): string[] {
	return official.slice(0, count).map((row) => row.team_name);
}

export function listByIndexes<T>(rows: readonly T[], indexes: readonly number[]): T[] {
	return indexes.map((index) => {
		const row = rows[index];
		if (row === undefined) {
			throw new Error('What-if index is outside the official list.');
		}
		return row;
	});
}

export type WeekBoardModel<T extends WhatIfParts> = {
	officialTeams: readonly T[];
	secondList: WhatIfBoard;
	secondTeams: T[];
	copyLink: string;
	resetPath: string;
	sharePath: string;
	citationPath: string;
	shareNames: string[];
};

export function weekBoardModel<T extends WhatIfParts>(input: {
	year: number;
	week: number;
	teams: readonly T[];
	search: string;
}): WeekBoardModel<T> {
	const secondList = orderWhatIf(input.teams, readWhatIfParam(input.search));
	return {
		officialTeams: input.teams,
		secondList,
		secondTeams: listByIndexes(input.teams, secondList.indexes),
		copyLink: copyWhatIfLink(input.year, input.week),
		resetPath: resetWhatIfLink(input.year, input.week, input.search),
		sharePath: officialSharePath(input.year, input.week),
		citationPath: officialSharePath(input.year, input.week),
		shareNames: officialShareNames(input.teams),
	};
}
