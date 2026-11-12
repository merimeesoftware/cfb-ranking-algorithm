import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { join } from 'node:path';
import { test } from 'node:test';
import { fileURLToPath } from 'node:url';
import { orderTeamsByElo } from '../src/lib/order.ts';
import {
	OFFICIAL_WEIGHTS,
	WHATIF_NOTICE,
	orderWhatIf,
	parseWhatIf,
	whatIfScore,
	type WhatIfParts,
	type WhatIfReason,
} from '../src/lib/whatif.ts';

globalThis.fetch = () => {
	throw new Error('what-if tests must not call the network');
};

const REPO_ROOT = fileURLToPath(new URL('../..', import.meta.url));

type WeekRow = WhatIfParts & {
	ordering_score?: number;
	final_ranking_score: number;
	momentum?: number | null;
};

function weekPath(year: 2024 | 2026): string {
	const path = join(REPO_ROOT, 'frontend', 'static', 'rankings', String(year), 'week-10.json');
	assert.equal(path.includes(`${join('rankings', '2025')}`), false);
	return path;
}

function loadWeek(year: 2024 | 2026): WeekRow[] {
	const data = JSON.parse(readFileSync(weekPath(year), 'utf8')) as {
		algo?: string;
		team_rankings: WeekRow[];
	};
	assert.equal(data.algo, 'v5.5');
	assert.ok(data.team_rankings.length > 25);
	return data.team_rankings.map((row) => ({ ...row }));
}

function official(rows: WeekRow[]): WeekRow[] {
	return orderTeamsByElo(rows);
}

function names(rows: readonly { team_name: string }[]): string[] {
	return rows.map((row) => row.team_name);
}

function assertUnstamped(board: ReturnType<typeof orderWhatIf>): void {
	assert.equal(board.official, false);
	assert.equal(board.cached, false);
	assert.equal(board.algo, null);
	assert.equal(JSON.stringify(board).includes('v5.5'), false);
	assert.throws(() => {
		(board as { algo: string | null }).algo = 'v5.5';
	});
	assert.throws(() => {
		(board as { official: boolean }).official = true;
	});
	assert.throws(() => {
		(board as { cached: boolean }).cached = true;
	});
}

function assertRejected(raw: string, reason: WhatIfReason, rows: WeekRow[]): void {
	const parsed = parseWhatIf(raw);
	assert.equal(parsed.ok, false);
	if (!parsed.ok) {
		assert.equal(parsed.reason, reason);
		assert.equal(parsed.notice, WHATIF_NOTICE);
		assert.equal(parsed.weights, null);
	}
	const before = names(rows);
	const board = orderWhatIf(rows, raw);
	assert.deepEqual(names(rows), before);
	assert.equal(board.ok, false);
	assert.equal(board.notice, WHATIF_NOTICE);
	assert.equal(board.reason, reason);
			assert.deepEqual([...board.names], before);
			assert.deepEqual([...board.indexes], rows.map((_, index) => index));
			assertUnstamped(board);
}

test('omitted and 100-0-0-0 stay on the official order', () => {
	for (const year of [2024, 2026] as const) {
		const rows = official(loadWeek(year));
		const before = names(rows);
		for (const raw of [undefined, null, '100-0-0-0'] as const) {
			const parsed = parseWhatIf(raw);
			assert.equal(parsed.ok, true);
			if (parsed.ok) {
				assert.deepEqual(parsed.weights, OFFICIAL_WEIGHTS);
				assert.equal(parsed.notice, null);
			}
			const board = orderWhatIf(rows, raw);
			assert.equal(board.ok, true);
			assert.equal(board.notice, null);
			assert.deepEqual([...board.names], before);
			assert.deepEqual(names(rows), before);
			assertUnstamped(board);
		}
		assert.ok(rows.every((row) => row.ordering_score === row.team_quality_score));
	}
});

test('80-15-5-0 matches the stored blend order and 70-30-0-0 matches v5.5', () => {
	const expected70 = {
		2024: ['Oregon', 'Ohio State', 'BYU', 'Miami', 'Indiana'],
		2026: ['Utah', 'Alabama', 'UCLA', 'Georgia', 'Notre Dame'],
	} as const;
	for (const year of [2024, 2026] as const) {
		const rows = official(loadWeek(year));
		const before = names(rows);
		const blend = orderWhatIf(rows, '80-15-5-0');
		const byStored = rows
			.map((row, index) => ({ row, index }))
			.sort((a, b) => {
				const byScore = b.row.final_ranking_score - a.row.final_ranking_score;
				if (byScore !== 0) return byScore;
				return a.index - b.index;
			})
			.map((item) => item.row.team_name);
		assert.deepEqual([...blend.names], byStored);
		assert.ok(blend.weights);
		let gap = 0;
		for (const row of rows) {
			gap = Math.max(
				gap,
				Math.abs(whatIfScore(row, blend.weights) - row.final_ranking_score)
			);
		}
		// The stored blend and this sum differ only by binary rounding.
		assert.ok(gap < 1e-9);
		const moved = orderWhatIf(rows, '70-30-0-0');
		assert.deepEqual([...moved.names].slice(0, 5), [...expected70[year]]);
		assert.deepEqual(
			[...moved.indexes].map((index) => rows[index]?.team_name),
			[...moved.names]
		);
		assert.equal(new Set(moved.scores).size, rows.length);
		assert.deepEqual(names(rows), before);
		assert.notDeepEqual([...moved.names], before);
		assertUnstamped(blend);
		assertUnstamped(moved);
	}
	const week2026 = official(loadWeek(2026));
	const moved = orderWhatIf(week2026, '70-30-0-0');
	assert.equal(moved.names.indexOf('Georgia'), 3);
	assert.deepEqual(names(official(loadWeek(2024))).slice(0, 5), [
		'Indiana',
		'Ohio State',
		'Oregon',
		'Georgia',
		'Notre Dame',
	]);
	assert.deepEqual(names(week2026).slice(0, 5), [
		'Georgia',
		'Utah',
		'Alabama',
		'Notre Dame',
		'UCLA',
	]);
});

test('a bad link is not renormalized and Heat stays 0', () => {
	const rows = official(loadWeek(2026));
	const cases: Array<[string, WhatIfReason]> = [
		['', 'missing'],
		['70-30-0', 'missing'],
		['70-30-0-0-0', 'extra'],
		['70-30-0-0.0', 'non-integer'],
		['+70-30-0-0', 'non-integer'],
		['070-30-0-0', 'non-integer'],
		['70-30-0- 0', 'non-integer'],
		['101-0-0-0', 'out-of-range'],
		['60-30-0-0', 'sum'],
		['0-0-0-0', 'sum'],
		['70-20-0-10', 'heat'],
		['99-0-0-1', 'heat'],
		['90-0-0-20', 'heat'],
	];
	for (const [raw, reason] of cases) {
		assertRejected(raw, reason, rows);
	}

	const highResume = {
		team_name: 'Resume',
		team_quality_score: 1000,
		record_score: 10000,
		conference_quality_score: 0,
		momentum: 50,
	};
	const highLook = {
		team_name: 'Look',
		team_quality_score: 2000,
		record_score: 0,
		conference_quality_score: 0,
		momentum: -50,
	};
	const pair = [highLook, highResume];
	const rejected = orderWhatIf(pair, '60-30-0-0');
	assert.deepEqual([...rejected.names], ['Look', 'Resume']);
	const applied = orderWhatIf(pair, '60-40-0-0');
	assert.deepEqual([...applied.names], ['Resume', 'Look']);

	const twin = { ...highLook, team_name: 'Look', momentum: 9999 };
	assert.equal(
		whatIfScore(highLook, OFFICIAL_WEIGHTS),
		whatIfScore(twin, { look: 100, resume: 0, league: 0, heat: 0 })
	);
	assert.equal(
		whatIfScore(highLook, { look: 70, resume: 30, league: 0, heat: 0 }),
		whatIfScore({ ...highLook, momentum: -9999 }, { look: 70, resume: 30, league: 0, heat: 0 })
	);
	assert.throws(() => whatIfScore(highLook, { look: 70, resume: 20, league: 0, heat: 10 }));
});

test('equal scores keep the official order', () => {
	const rows: WhatIfParts[] = [
		{ team_name: 'First', team_quality_score: 10, record_score: 10, conference_quality_score: 10 },
		{ team_name: 'Second', team_quality_score: 10, record_score: 10, conference_quality_score: 10 },
	];
	const board = orderWhatIf(rows, '50-25-25-0');
	assert.deepEqual([...board.names], ['First', 'Second']);
	assert.equal(board.scores[0], board.scores[1]);
	assertUnstamped(board);
});
