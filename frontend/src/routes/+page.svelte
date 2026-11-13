<script lang="ts">
	import SeoHead from '$lib/components/SeoHead.svelte';
	import BoardMast from '$lib/components/BoardMast.svelte';
	import {
		BRAND_NAME,
		RATING_NAME,
		TAGLINE,
		pageTitle,
	} from '$lib/brand';
	import { shownGap, toBoardRows, type BoardRow } from '$lib/boardDisplay';
	import type { Team } from '$lib/types';

	export let data: {
		seed: {
			year: number;
			week: number;
			teams: Team[];
			teamCount: number;
		} | null;
		story: { headline?: string; paragraphs?: string[] } | null;
		prevRanks: Record<string, number>;
	};

	// svelte-ignore unused-export-let
	export let params: Record<string, string> = {};

	const seed = data.seed;
	const rows: BoardRow[] = seed ? toBoardRows(seed.teams) : [];
	const year = seed?.year ?? 0;
	const week = seed?.week ?? 0;
	let query = '';
	let showSlice = false;
	let showAll = false;
	let openRank: number | null = null;

	$: visible = rows.filter((row) => rowVisible(row));
	$: openRow = rows.find((row) => row.rank === openRank) ?? null;

	function rowVisible(row: BoardRow): boolean {
		const needle = query.trim().toLowerCase();
		const named = needle.length === 0 || row.name.toLowerCase().includes(needle);
		if (!named) return false;
		if (needle.length > 0) return true;
		if (row.rank <= 13) return true;
		if (row.rank <= 16) return showSlice || showAll;
		return showAll;
	}

	function toggle(row: BoardRow) {
		openRank = openRank === row.rank ? null : row.rank;
	}

	function hasNeighbor(rank: number, delta: number): boolean {
		return rows.some((row) => row.rank === rank + delta);
	}

	function neighbor(rank: number, delta: number): BoardRow {
		const row = rows.find((item) => item.rank === rank + delta);
		if (!row) throw new Error('missing neighbor');
		return row;
	}

	$: earlyLine = earlySummary(rows);

	function earlySummary(list: BoardRow[]): string {
		const early = list.filter((row) => row.early).length;
		if (early === 0) return 'Early: none this week.';
		if (early === list.length) return 'Early is on for every team.';
		return 'Early is on when a team has fewer than 3 games.';
	}

	function gapLine(row: BoardRow): string {
		const parts: string[] = [];
		if (hasNeighbor(row.rank, -1)) {
			const above = neighbor(row.rank, -1);
			parts.push(`${shownGap(above.tr, row.tr)} behind No. ${above.rank} ${above.name}`);
		}
		if (hasNeighbor(row.rank, 1)) {
			const below = neighbor(row.rank, 1);
			parts.push(`${shownGap(row.tr, below.tr)} ahead of No. ${below.rank} ${below.name}`);
		}
		return parts.join(', ');
	}
</script>

<SeoHead
	title={pageTitle([year && week ? `${year} Week ${week}` : 'This week', TAGLINE])}
	description={`${BRAND_NAME} ${RATING_NAME} board for ${year} Week ${week}. ${TAGLINE}`}
	canonicalPath="/"
/>

<BoardMast {year} {week} showLines />

<main>
	<section id="board" aria-labelledby="board-title">
		<h2 id="board-title" class="sr-only">{year} week {week} board</h2>
		{#if !seed}
			<p>This week isn’t published yet.</p>
		{:else}
			<div class="table-wrap" tabindex="0" role="region" aria-labelledby="board-caption">
				<table>
					<caption id="board-caption">{year} week {week}. {rows.length} teams. Ordered by {RATING_NAME}.</caption>
					<thead>
						<tr>
							<th scope="col">Team</th>
							<th scope="col">Record</th>
							<th scope="col">Record quality</th>
							<th scope="col" title="How good they look right now. This sets the order.">{RATING_NAME}</th>
							<th scope="col" class="col-early">Early</th>
						</tr>
					</thead>
					<tbody id="board-body">
						{#each visible as row (row.rank)}
							<tr class:band={row.rank <= 12} class:rest={row.rank >= 14} class:shown={row.rank >= 14} data-name={row.name}>
								<th scope="row">
									<span class="rk">{row.rank}</span>
									<span class="team-cell">
										<span class="pip" style="background:{row.color}"></span>
										<span class="name-row">
											<button
												type="button"
												class="name row-toggle"
												aria-expanded={openRank === row.rank}
												on:click={() => toggle(row)}
											>{row.name}</button>
											<span class="tr-inline">{row.tr}</span>
										</span>
										<span class="conf">{row.conference}</span>
									</span>
								</th>
								<td data-label="Record">{row.record}</td>
								<td data-label="Record quality">{row.quality}</td>
								<td class="tr tr-col" data-label={RATING_NAME}>{row.tr}</td>
								<td class="col-early" data-label="Early">
									<span aria-hidden="true">{row.early ? 'Early' : '—'}</span>
									<span class="sr-only">{row.early ? `Early on. ${row.games} games.` : `Early off. ${row.games} games.`}</span>
								</td>
							</tr>
							{#if openRow && openRow.rank === row.rank}
								<tr class="detail">
									<td colspan="5">
										<ol class="ladder">
											{#if hasNeighbor(row.rank, -1)}
												{@const above = neighbor(row.rank, -1)}
												<li class="rung">
													<span class="rk">{above.rank}</span>
													<span class="name">{above.name}</span>
													<span class="who">{above.overall} · {above.conference}</span>
													<p class="elo-num">{above.tr}</p>
												</li>
												<li class="between">{shownGap(above.tr, row.tr)} behind No. {above.rank} {above.name}</li>
											{/if}
											<li class="rung subject">
												<span class="rk">{row.rank}</span>
												<span class="pip" style="background:{row.color}"></span>
												<span class="name">{row.name}</span>
												<span class="who">{row.conference} · {row.record}</span>
												<p class="elo-num">{row.tr}</p>
											</li>
											{#if hasNeighbor(row.rank, 1)}
												{@const below = neighbor(row.rank, 1)}
												<li class="between">{shownGap(row.tr, below.tr)} ahead of No. {below.rank} {below.name}</li>
												<li class="rung">
													<span class="rk">{below.rank}</span>
													<span class="name">{below.name}</span>
													<span class="who">{below.overall} · {below.conference}</span>
													<p class="elo-num">{below.tr}</p>
												</li>
											{/if}
										</ol>
										<p>{RATING_NAME} {row.tr}. This sets the rank.{gapLine(row) ? ` ${gapLine(row)}.` : ''}</p>
										<dl class="constants">
											<dt>Record</dt>
											<dd>{row.record}. Beside the rank. It does not set the rank.</dd>
											<dt>Resume</dt>
											<dd>Who they beat, ranked. {row.qualityWins} quality wins, {row.qualityLosses} quality losses, {row.badLosses} bad losses. {row.powerLine} against Power 4.</dd>
											<dt>Schedule</dt>
											<dd>{row.scheduleRank ? `Schedule rank ${row.scheduleRank} of ${row.teamCount}. ` : ''}It does not set the order.</dd>
											<dt>Record quality</dt>
											<dd>{row.ahead} wins ahead of what {RATING_NAME} expected. {row.soft}% of the wins are soft.{row.blendRank ? ` The old blend has them No. ${row.blendRank}.` : ''}</dd>
											<dt>Early</dt>
											<dd>{row.early ? `On. ${row.games} games.` : `Off. ${row.games} games.`}</dd>
										</dl>
										<p class="note">Game scores aren’t on this page.</p>
									</td>
								</tr>
							{/if}
						{/each}
					</tbody>
				</table>
			</div>
			<p class="early-once">{earlyLine}</p>
			<p class="find"><label>Find your team <input type="search" autocomplete="off" bind:value={query}></label></p>
			<p><button type="button" class="btn quiet" on:click={() => (showSlice = true)}>Show ranks 14–16</button></p>
			<p><button type="button" class="btn quiet" on:click={() => (showAll = true)}>Show the full board</button></p>
			<details>
				<summary>How to read this</summary>
				<p>{RATING_NAME} sets the order. Record quality is wins ahead of what {RATING_NAME} expected, and the share of wins that are soft. Early is on when a team has fewer than 3 games. None of these columns change the rank. Gold marks ranks 1 through 12. Ranks 13 and below use ink.</p>
			</details>
		{/if}
	</section>
</main>
