<script lang="ts">
	import BoardMast from '$lib/components/BoardMast.svelte';
	import { BRAND_NAME, EARLY_SEASON_NOTE, NAV, RATING_NAME, pageTitle } from '$lib/brand';

	export let data: {
		year: number;
		week: number;
		official: string[];
		oldBlend: string[];
		whatIf: string[];
		parts: { name: string; look: number; resume: number; league: number }[];
		teamCount: number;
		moved: number;
		meanGap: string;
		officialLeader: string;
	};

	// svelte-ignore unused-export-let
	export let params: Record<string, string> = {};

	let look = 70;
	let resume = 30;
	let league = 0;

	function rebalance(changed: 'look' | 'resume' | 'league', value: number) {
		const current = { look, resume, league };
		const others = (['look', 'resume', 'league'] as const).filter((key) => key !== changed);
		const rest = 100 - value;
		const sum = current[others[0]] + current[others[1]];
		if (sum === 0) {
			const first = Math.floor(rest / 2);
			current[others[0]] = first;
			current[others[1]] = rest - first;
		} else {
			const share = Math.round((rest * current[others[0]]) / sum);
			current[others[0]] = share;
			current[others[1]] = rest - share;
		}
		current[changed] = value;
		look = current.look;
		resume = current.resume;
		league = current.league;
	}

	function reset() {
		look = 100;
		resume = 0;
		league = 0;
	}

	$: whatIfNames = data.parts
		.map((row, index) => ({
			name: row.name,
			index,
			score: (look / 100) * row.look + (resume / 100) * row.resume + (league / 100) * row.league,
		}))
		.sort((a, b) => b.score - a.score || a.index - b.index)
		.slice(0, 5);
	$: rankedNames = data.parts
		.map((row, index) => ({
			name: row.name,
			index,
			score: (look / 100) * row.look + (resume / 100) * row.resume + (league / 100) * row.league,
		}))
		.sort((a, b) => b.score - a.score || a.index - b.index);
	$: georgiaPlace = rankedNames.findIndex((row) => row.name === 'Georgia');
	$: georgiaOfficial = data.parts.findIndex((row) => row.name === 'Georgia');
	$: math = `${(look / 100).toFixed(2)} × how they look + ${(resume / 100).toFixed(2)} × resume + ${(league / 100).toFixed(2)} × league strength.`;
</script>

<svelte:head>
	<title>{pageTitle([NAV.formula])}</title>
</svelte:head>

<BoardMast year={data.year} week={data.week} />

<main>
	<section id="formula" aria-labelledby="formula-title">
		<h1 id="formula-title">{NAV.formula}</h1>
		<div class="pair">
			<article class="side">
				<h3>The order</h3>
				<p class="elo-num" style="font-size:1.35rem">{RATING_NAME}</p>
				<p>How good they look right now. This sets the order. Record, record quality, and early sit beside it.</p>
			</article>
			<article class="side">
				<h3>Old blend</h3>
				<p>For comparison, the old blend: 0.80 × how they look + 0.15 × resume + 0.05 × league strength. The board no longer sorts by it.</p>
				<p>The parts are not scaled to 0–100 before weighting. On {data.year} week {data.week}, {data.moved} of {data.teamCount} teams sit in a different place. The average gap is {data.meanGap} places.</p>
			</article>
		</div>
		<p>How they look is the Elo rating in the code.</p>
		<dl class="constants">
			<dt>Step size</dt>
			<dd>50. A postseason game multiplies it by 0.65, so 32.5.</dd>
			<dt>Margin</dt>
			<dd>The natural log of the margin plus 1. There is no cap.</dd>
			<dt>Home field</dt>
			<dd>50 in the regular season, 20 in the postseason, 0 on a neutral field. It changes the expectation only.</dd>
			<dt>Upset</dt>
			<dd>A Group of 5 win over a Power 4 team multiplies the step by 1.12. There is no other upset bonus.</dd>
			<dt>Who plays whom</dt>
			<dd>Power 4 vs Power 4 is 1.0. Power 4 vs Group of 5 is 0.8. Group of 5 vs Group of 5 is 0.65. FBS vs FCS is 0.2. Anything else is 0.1.</dd>
			<dt>Ceiling</dt>
			<dd>No winner’s rating goes above 1,850. The loser still drops the full step.</dd>
			<dt>Opening</dt>
			<dd>{EARLY_SEASON_NOTE}</dd>
			<dt>Fade</dt>
			<dd>max(0, 0.7 × (12 − week) / 11). Week 1 keeps 0.7. Week 10 keeps 0.127. Week 12 keeps 0.</dd>
			<dt>Heat</dt>
			<dd>Heat is not in the order. It hasn’t passed its test yet.</dd>
		</dl>
		<div class="whatif">
			<p class="example">Example only</p>
			<h3>What-if. This does not change the official board.</h3>
			<div class="sliders">
				<div class="slider-row">
					<label for="sl-look">How they look</label>
					<output id="out-look" for="sl-look">{look}</output>
					<input id="sl-look" type="range" min="0" max="100" value={look} aria-valuetext="{look} percent" on:input={(event) => rebalance('look', Number(event.currentTarget.value))}>
				</div>
				<div class="slider-row">
					<label for="sl-resume">Resume</label>
					<output id="out-resume" for="sl-resume">{resume}</output>
					<input id="sl-resume" type="range" min="0" max="100" value={resume} aria-valuetext="{resume} percent" on:input={(event) => rebalance('resume', Number(event.currentTarget.value))}>
				</div>
				<div class="slider-row">
					<label for="sl-league">League strength</label>
					<output id="out-league" for="sl-league">{league}</output>
					<input id="sl-league" type="range" min="0" max="100" value={league} aria-valuetext="{league} percent" on:input={(event) => rebalance('league', Number(event.currentTarget.value))}>
				</div>
			</div>
			<p class="math" id="math">{math}</p>
			<p>Heat is not in the order. It hasn’t passed its test yet.</p>
			<div class="actions">
				<button type="button" class="btn quiet" on:click={reset}>Reset to official</button>
			</div>
			<div class="lists">
				<div>
					<h4>Official</h4>
					<ol>{#each data.official as name}<li>{name}</li>{/each}</ol>
				</div>
				<div>
					<h4>Old blend</h4>
					<ol>{#each data.oldBlend as name}<li>{name}</li>{/each}</ol>
				</div>
				<div>
					<h4>This what-if</h4>
					<ol>{#each whatIfNames as row}<li>{row.name}</li>{/each}</ol>
				</div>
			</div>
			{#if georgiaPlace >= 0 && georgiaOfficial >= 0}
				<p>At these weights Georgia is No. {georgiaPlace + 1} on the what-if list. The official board still has Georgia No. {georgiaOfficial + 1}.</p>
			{/if}
			<p class="note">Old blend. Weights 80 / 15 / 5 / 0. A comparison, not the board.</p>
		</div>
		<p class="note">Figures from the stored {data.year} weeks. Algo label v5.5.</p>
	</section>
</main>

<p class="sr-only">{BRAND_NAME}</p>
