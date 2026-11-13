import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { join } from 'node:path';
import { test } from 'node:test';
import { fileURLToPath } from 'node:url';
import { orderTeamsByElo } from '../src/lib/order.ts';
import {
	copyWhatIfLink,
	officialShareNames,
	officialSharePath,
	readWhatIfParam,
	resetWhatIfLink,
	weekBoardModel,
} from '../src/lib/whatifPage.ts';
import type { WhatIfParts } from '../src/lib/whatif.ts';

globalThis.fetch = () => {
	throw new Error('what-if page tests must not call the network');
};

const REPO_ROOT = fileURLToPath(new URL('../..', import.meta.url));
const FRONTEND = join(REPO_ROOT, 'frontend');

type WeekRow = WhatIfParts & { ordering_score?: number };

function loadWeek(year: 2024 | 2026): WeekRow[] {
	const path = join(FRONTEND, 'static', 'rankings', String(year), 'week-10.json');
	assert.equal(path.includes(join('rankings', '2025')), false);
	const data = JSON.parse(readFileSync(path, 'utf8')) as { team_rankings: WeekRow[] };
	return orderTeamsByElo(data.team_rankings.map((row) => ({ ...row })));
}

function names(rows: readonly { team_name: string }[]): string[] {
	return rows.map((row) => row.team_name);
}

test('the copy link is the week path plus 70-30-0-0, and reset clears it', () => {
	assert.equal(copyWhatIfLink(2026, 10), '/2026/week/10?whatif=70-30-0-0');
	assert.equal(copyWhatIfLink(2024, 10), '/2024/week/10?whatif=70-30-0-0');
	assert.equal(copyWhatIfLink(2026, 10).includes('/api'), false);
	assert.equal(copyWhatIfLink(2026, 10).includes('http'), false);
	assert.equal(resetWhatIfLink(2026, 10, '?whatif=70-30-0-0'), '/2026/week/10');
	assert.equal(resetWhatIfLink(2026, 10, '?whatif=80-15-5-0'), '/2026/week/10');
	assert.equal(officialSharePath(2026, 10), '/2026/week/10');
	assert.equal(readWhatIfParam(''), undefined);
	assert.equal(readWhatIfParam('?whatif=70-30-0-0&whatif=100-0-0-0'), '');
});

test('the second list reorders and the official list, share, and citation do not', () => {
	for (const year of [2024, 2026] as const) {
		const teams = loadWeek(year);
		const before = names(teams);
		const model = weekBoardModel({
			year,
			week: 10,
			teams,
			search: '?whatif=70-30-0-0',
		});
		assert.equal(model.officialTeams, teams);
		assert.deepEqual(names(teams), before);
		assert.deepEqual(model.shareNames, before.slice(0, 5));
		assert.deepEqual(officialShareNames(teams), before.slice(0, 5));
		assert.notDeepEqual(names(model.secondTeams).slice(0, 5), before.slice(0, 5));
		assert.equal(model.secondList.official, false);
		assert.equal(model.secondList.cached, false);
		assert.equal(model.secondList.algo, null);
		assert.equal(JSON.stringify(model.secondList).includes('v5.5'), false);
		assert.equal(model.copyLink, `/${year}/week/10?whatif=70-30-0-0`);
		assert.equal(model.sharePath, `/${year}/week/10`);
		assert.equal(model.citationPath, model.sharePath);
		assert.equal(model.resetPath, `/${year}/week/10`);
		assert.equal(model.copyLink.includes('/api'), false);
	}

	const teams = loadWeek(2026);
	const moved = weekBoardModel({
		year: 2026,
		week: 10,
		teams,
		search: '?whatif=70-30-0-0',
	});
	assert.deepEqual(names(moved.secondTeams).slice(0, 5), [
		'Utah',
		'Alabama',
		'UCLA',
		'Georgia',
		'Notre Dame',
	]);
	assert.deepEqual(moved.shareNames, [
		'Georgia',
		'Utah',
		'Alabama',
		'Notre Dame',
		'UCLA',
	]);

	const bad = weekBoardModel({
		year: 2026,
		week: 10,
		teams,
		search: '?whatif=60-30-0-0&whatif=70-30-0-0',
	});
	assert.equal(bad.secondList.ok, false);
	assert.ok(bad.secondList.notice);
	assert.deepEqual(names(bad.secondTeams), names(teams));
	assert.equal(bad.copyLink, '/2026/week/10?whatif=70-30-0-0');

	const plain = weekBoardModel({ year: 2026, week: 10, teams, search: '' });
	assert.equal(plain.secondList.ok, true);
	assert.equal(plain.secondList.notice, null);
	assert.deepEqual(names(plain.secondTeams), names(teams));
});

test('the week page keeps the second list and copy link off the visible template', () => {
	const page = readFileSync(
		join(FRONTEND, 'src', 'routes', '[year]', 'week', '[week]', '+page.svelte'),
		'utf8'
	);
	const template = page.split('</script>').slice(1).join('</script>');
	assert.match(page, /weekBoardModel/);
	assert.equal(template.includes('whatif'), false);
	assert.equal(template.includes('secondList'), false);
	assert.equal(template.includes('secondTeams'), false);
	assert.equal(template.includes('copyLink'), false);
	assert.equal(template.includes('<input'), false);
	assert.match(template, /data\.teams/);
	assert.match(template, /BoardActions/);
	const home = readFileSync(join(FRONTEND, 'src', 'lib', 'stores', 'rankings.ts'), 'utf8');
	const api = readFileSync(join(FRONTEND, 'src', 'lib', 'api.ts'), 'utf8');
	const share = readFileSync(join(FRONTEND, 'src', 'lib', 'components', 'BoardActions.svelte'), 'utf8');
	assert.equal(home.includes('whatif'), false);
	assert.equal(api.includes('whatif'), false);
	assert.equal(share.includes('whatif'), false);
});
