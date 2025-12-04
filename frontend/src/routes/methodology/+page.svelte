<script lang="ts">
	// Methodology page
	let expandedSection: string | null = null;
	
	function toggleSection(section: string) {
		expandedSection = expandedSection === section ? null : section;
	}
</script>

<svelte:head>
	<title>Methodology | CFB Rankings</title>
</svelte:head>

<div class="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8 py-6 sm:py-10">
	<!-- Hero Section -->
	<div class="text-center mb-8">
		<h1 class="text-3xl sm:text-4xl font-bold text-gray-900 dark:text-white">
			How the Rankings Work
		</h1>
		<p class="mt-2 text-lg text-gray-600 dark:text-gray-400">
			Version 3.9 — Balancing Predictive Power with Deserving Resume
		</p>
	</div>

	<!-- Formula Card -->
	<div class="card p-6 mb-6">
		<h2 class="text-xl font-semibold text-gray-900 dark:text-white mb-4 flex items-center gap-2">
			<svg class="w-6 h-6 text-primary-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
				<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 7h6m0 10v-3m-3 3h.01M9 17h.01M9 14h.01M12 14h.01M15 11h.01M12 11h.01M9 11h.01M7 21h10a2 2 0 002-2V5a2 2 0 00-2-2H7a2 2 0 00-2 2v14a2 2 0 002 2z" />
			</svg>
			The Formula
		</h2>
		<div class="bg-gray-100 dark:bg-gray-700 rounded-lg p-4 font-mono text-center text-lg">
			<span class="text-primary-600 dark:text-primary-400">FRS</span> = 
			(<span class="text-blue-600 dark:text-blue-400">0.55</span> × TeamQuality) + 
			(<span class="text-green-600 dark:text-green-400">0.35</span> × RecordScore) + 
			(<span class="text-purple-600 dark:text-purple-400">0.10</span> × ConfQuality)
		</div>
	</div>

	<!-- Components Grid -->
	<div class="grid md:grid-cols-3 gap-4 mb-8">
		<!-- Team Quality -->
		<div class="card p-5">
			<div class="flex items-center gap-3 mb-3">
				<div class="w-10 h-10 rounded-full bg-blue-100 dark:bg-blue-900/50 flex items-center justify-center">
					<svg class="w-5 h-5 text-blue-600 dark:text-blue-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
						<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13 7h8m0 0v8m0-8l-8 8-4-4-6 6" />
					</svg>
				</div>
				<h3 class="font-semibold text-gray-900 dark:text-white">Team Quality (55%)</h3>
			</div>
			<p class="text-sm text-gray-600 dark:text-gray-400">
				The Elo rating. Measures pure team strength based on who you played and margin of victory. 
				Uses asymmetric updates where upsets are rewarded more than expected wins.
			</p>
			<button 
				on:click={() => toggleSection('teamQuality')}
				class="mt-3 text-sm text-primary-600 dark:text-primary-400 hover:underline flex items-center gap-1"
			>
				{expandedSection === 'teamQuality' ? 'Show Less' : 'Learn More'}
				<svg class="w-4 h-4 transition-transform {expandedSection === 'teamQuality' ? 'rotate-180' : ''}" fill="none" stroke="currentColor" viewBox="0 0 24 24">
					<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 9l-7 7-7-7" />
				</svg>
			</button>
		</div>

		<!-- Record Score -->
		<div class="card p-5">
			<div class="flex items-center gap-3 mb-3">
				<div class="w-10 h-10 rounded-full bg-green-100 dark:bg-green-900/50 flex items-center justify-center">
					<svg class="w-5 h-5 text-green-600 dark:text-green-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
						<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2m-3 7h3m-3 4h3m-6-4h.01M9 16h.01" />
					</svg>
				</div>
				<h3 class="font-semibold text-gray-900 dark:text-white">Record Score (35%)</h3>
			</div>
			<p class="text-sm text-gray-600 dark:text-gray-400">
				A composite of Winning %, Strength of Schedule (SoS), and Strength of Victory (SoV). 
				Rewards teams for quality wins against tough opponents.
			</p>
			<button 
				on:click={() => toggleSection('recordScore')}
				class="mt-3 text-sm text-primary-600 dark:text-primary-400 hover:underline flex items-center gap-1"
			>
				{expandedSection === 'recordScore' ? 'Show Less' : 'Learn More'}
				<svg class="w-4 h-4 transition-transform {expandedSection === 'recordScore' ? 'rotate-180' : ''}" fill="none" stroke="currentColor" viewBox="0 0 24 24">
					<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 9l-7 7-7-7" />
				</svg>
			</button>
		</div>

		<!-- Conference Quality -->
		<div class="card p-5">
			<div class="flex items-center gap-3 mb-3">
				<div class="w-10 h-10 rounded-full bg-purple-100 dark:bg-purple-900/50 flex items-center justify-center">
					<svg class="w-5 h-5 text-purple-600 dark:text-purple-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
						<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M17 20h5v-2a3 3 0 00-5.356-1.857M17 20H7m10 0v-2c0-.656-.126-1.283-.356-1.857M7 20H2v-2a3 3 0 015.356-1.857M7 20v-2c0-.656.126-1.283.356-1.857m0 0a5.002 5.002 0 019.288 0M15 7a3 3 0 11-6 0 3 3 0 016 0z" />
					</svg>
				</div>
				<h3 class="font-semibold text-gray-900 dark:text-white">Conference Quality (10%)</h3>
			</div>
			<p class="text-sm text-gray-600 dark:text-gray-400">
				Contextual boost for playing in stronger leagues. Weighted by P4 vs P4 out-of-conference performance.
			</p>
			<button 
				on:click={() => toggleSection('confQuality')}
				class="mt-3 text-sm text-primary-600 dark:text-primary-400 hover:underline flex items-center gap-1"
			>
				{expandedSection === 'confQuality' ? 'Show Less' : 'Learn More'}
				<svg class="w-4 h-4 transition-transform {expandedSection === 'confQuality' ? 'rotate-180' : ''}" fill="none" stroke="currentColor" viewBox="0 0 24 24">
					<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 9l-7 7-7-7" />
				</svg>
			</button>
		</div>
	</div>

	<!-- Expanded Sections -->
	{#if expandedSection === 'teamQuality'}
		<div class="card p-6 mb-8 border-l-4 border-blue-500">
			<h3 class="text-lg font-semibold text-gray-900 dark:text-white mb-4 flex items-center gap-2">
				<svg class="w-5 h-5 text-blue-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
					<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13 7h8m0 0v8m0-8l-8 8-4-4-6 6" />
				</svg>
				Team Quality — Deep Dive
			</h3>
			
			<div class="space-y-6">
				<!-- Initial Ratings -->
				<div>
					<h4 class="font-medium text-gray-900 dark:text-white mb-2">Starting Elo Ratings</h4>
					<p class="text-sm text-gray-600 dark:text-gray-400 mb-3">
						Each team begins the season with a tier-based initial rating, optionally blended with historical performance:
					</p>
					<div class="grid grid-cols-3 gap-3 text-center">
						<div class="bg-blue-50 dark:bg-blue-900/30 rounded-lg p-3">
							<div class="text-2xl font-bold text-blue-600 dark:text-blue-400">1500</div>
							<div class="text-xs text-gray-600 dark:text-gray-400">Power 4</div>
						</div>
						<div class="bg-green-50 dark:bg-green-900/30 rounded-lg p-3">
							<div class="text-2xl font-bold text-green-600 dark:text-green-400">1200</div>
							<div class="text-xs text-gray-600 dark:text-gray-400">Group of 5</div>
						</div>
						<div class="bg-gray-50 dark:bg-gray-700/50 rounded-lg p-3">
							<div class="text-2xl font-bold text-gray-600 dark:text-gray-400">900</div>
							<div class="text-xs text-gray-600 dark:text-gray-400">FCS</div>
						</div>
					</div>
				</div>

				<!-- Elo Update Formula -->
				<div>
					<h4 class="font-medium text-gray-900 dark:text-white mb-2">How Elo Updates Work</h4>
					<div class="bg-gray-100 dark:bg-gray-700 rounded-lg p-4 font-mono text-sm mb-3">
						Δ = K × Matchup_Weight × MoV × (Actual - Expected)
					</div>
					<div class="space-y-2 text-sm text-gray-600 dark:text-gray-400">
						<div class="flex gap-2">
							<span class="font-medium text-gray-900 dark:text-white w-32">K-factor:</span>
							<span>Base volatility (40). Higher = more dramatic swings per game.</span>
						</div>
						<div class="flex gap-2">
							<span class="font-medium text-gray-900 dark:text-white w-32">Expected:</span>
							<span>Logistic probability: 1 / (1 + 10^((R_loser - R_winner) / 400))</span>
						</div>
						<div class="flex gap-2">
							<span class="font-medium text-gray-900 dark:text-white w-32">MoV:</span>
							<span>log(score_diff + 1) — Logarithmic to prevent blowout exploitation</span>
						</div>
					</div>
				</div>

				<!-- Matchup Weights -->
				<div>
					<h4 class="font-medium text-gray-900 dark:text-white mb-2">Tier Matchup Weights</h4>
					<p class="text-sm text-gray-600 dark:text-gray-400 mb-3">
						Different matchups have different weights to prevent artificial inflation:
					</p>
					<div class="overflow-x-auto">
						<table class="w-full text-sm">
							<thead>
								<tr class="border-b border-gray-200 dark:border-gray-600">
									<th class="text-left py-2 text-gray-900 dark:text-white">Matchup</th>
									<th class="text-center py-2 text-gray-900 dark:text-white">Weight</th>
									<th class="text-left py-2 text-gray-900 dark:text-white">Rationale</th>
								</tr>
							</thead>
							<tbody class="text-gray-600 dark:text-gray-400">
								<tr class="border-b border-gray-100 dark:border-gray-700">
									<td class="py-2">P4 vs P4</td>
									<td class="text-center font-mono">1.0</td>
									<td>Full exchange; competitive games</td>
								</tr>
								<tr class="border-b border-gray-100 dark:border-gray-700">
									<td class="py-2">P4 vs G5</td>
									<td class="text-center font-mono">0.8</td>
									<td>Reduced; expected P4 advantage</td>
								</tr>
								<tr class="border-b border-gray-100 dark:border-gray-700">
									<td class="py-2">G5 vs G5</td>
									<td class="text-center font-mono">0.5</td>
									<td>Dampened to prevent G5 inflation</td>
								</tr>
								<tr class="border-b border-gray-100 dark:border-gray-700">
									<td class="py-2">FBS vs FCS</td>
									<td class="text-center font-mono">0.2</td>
									<td>Minimal; separate ecosystem</td>
								</tr>
								<tr>
									<td class="py-2">FCS vs FCS</td>
									<td class="text-center font-mono">0.1</td>
									<td>Isolated from FBS pool</td>
								</tr>
							</tbody>
						</table>
					</div>
				</div>

				<!-- Iterative Solver -->
				<div>
					<h4 class="font-medium text-gray-900 dark:text-white mb-2">Iterative Solver (3 Passes)</h4>
					<p class="text-sm text-gray-600 dark:text-gray-400">
						The season is simulated 3 times. Early-season games are re-evaluated using end-of-season opponent strength, 
						ensuring fair assessment of early performance when opponent quality was still unknown.
					</p>
				</div>
			</div>
		</div>
	{/if}

	{#if expandedSection === 'recordScore'}
		<div class="card p-6 mb-8 border-l-4 border-green-500">
			<h3 class="text-lg font-semibold text-gray-900 dark:text-white mb-4 flex items-center gap-2">
				<svg class="w-5 h-5 text-green-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
					<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2m-3 7h3m-3 4h3m-6-4h.01M9 16h.01" />
				</svg>
				Record Score — Deep Dive
			</h3>
			
			<div class="space-y-6">
				<!-- Formula -->
				<div>
					<h4 class="font-medium text-gray-900 dark:text-white mb-2">Record Score Formula</h4>
					<div class="bg-gray-100 dark:bg-gray-700 rounded-lg p-4 font-mono text-sm mb-3">
						RecordScore = 1000 + (WeightedWinPct × 1000) + SoV_Bonus + SoS_Score
					</div>
				</div>

				<!-- Weighted Win % -->
				<div>
					<h4 class="font-medium text-gray-900 dark:text-white mb-2">1. Weighted Win Percentage</h4>
					<p class="text-sm text-gray-600 dark:text-gray-400 mb-3">
						Road wins count 10% more than home wins to reward teams who win in hostile environments:
					</p>
					<div class="bg-gray-100 dark:bg-gray-700 rounded-lg p-4 font-mono text-sm mb-3">
						WeightedWinPct = ((HomeWins × 1.0) + (RoadWins × 1.1)) / TotalGames
					</div>
					<div class="bg-green-50 dark:bg-green-900/20 rounded-lg p-3 text-sm">
						<span class="font-medium text-green-700 dark:text-green-300">Example:</span>
						<span class="text-gray-600 dark:text-gray-400"> 10-2 with 7 home wins, 3 road wins → (7×1.0 + 3×1.1) / 12 = 0.858 → +858 points</span>
					</div>
				</div>

				<!-- SoV -->
				<div>
					<h4 class="font-medium text-gray-900 dark:text-white mb-2">2. Strength of Victory (SoV)</h4>
					<p class="text-sm text-gray-600 dark:text-gray-400 mb-3">
						Bonus points for beating quality opponents. Rewards WHO you beat, not just how many:
					</p>
					<div class="bg-gray-100 dark:bg-gray-700 rounded-lg p-4 font-mono text-sm mb-3">
						SoV_Bonus = (AvgWinElo - 1200) × 0.5 &nbsp;&nbsp;<span class="text-gray-500">[if AvgWinElo > 1200]</span>
					</div>
					<div class="grid grid-cols-3 gap-3 text-center text-sm">
						<div class="bg-yellow-50 dark:bg-yellow-900/20 rounded-lg p-2">
							<div class="font-bold text-yellow-600 dark:text-yellow-400">+300 pts</div>
							<div class="text-xs text-gray-600 dark:text-gray-400">Avg Win Elo: 1800</div>
						</div>
						<div class="bg-green-50 dark:bg-green-900/20 rounded-lg p-2">
							<div class="font-bold text-green-600 dark:text-green-400">+150 pts</div>
							<div class="text-xs text-gray-600 dark:text-gray-400">Avg Win Elo: 1500</div>
						</div>
						<div class="bg-gray-50 dark:bg-gray-700/50 rounded-lg p-2">
							<div class="font-bold text-gray-600 dark:text-gray-400">+0 pts</div>
							<div class="text-xs text-gray-600 dark:text-gray-400">Avg Win Elo: &lt;1200</div>
						</div>
					</div>
				</div>

				<!-- SoS -->
				<div>
					<h4 class="font-medium text-gray-900 dark:text-white mb-2">3. Strength of Schedule (SoS)</h4>
					<p class="text-sm text-gray-600 dark:text-gray-400 mb-3">
						Rewards tough schedules using logarithmic scaling for smoother differentiation:
					</p>
					<div class="bg-gray-100 dark:bg-gray-700 rounded-lg p-4 font-mono text-sm mb-3">
						<div>if AvgOppElo > 1400:</div>
						<div class="ml-4">SoS = log(AvgOppElo - 1400) × 150</div>
						<div>else:</div>
						<div class="ml-4">SoS = (AvgOppElo - 1400) × 0.5 &nbsp;<span class="text-gray-500"># penalty</span></div>
					</div>
					<div class="overflow-x-auto">
						<table class="w-full text-sm">
							<thead>
								<tr class="border-b border-gray-200 dark:border-gray-600">
									<th class="text-left py-2 text-gray-900 dark:text-white">Avg Opponent Elo</th>
									<th class="text-center py-2 text-gray-900 dark:text-white">SoS Score</th>
									<th class="text-left py-2 text-gray-900 dark:text-white">Interpretation</th>
								</tr>
							</thead>
							<tbody class="text-gray-600 dark:text-gray-400">
								<tr class="border-b border-gray-100 dark:border-gray-700">
									<td class="py-1">1400 (weak)</td>
									<td class="text-center font-mono">~0</td>
									<td>Baseline</td>
								</tr>
								<tr class="border-b border-gray-100 dark:border-gray-700">
									<td class="py-1">1500 (average)</td>
									<td class="text-center font-mono">~150</td>
									<td>Standard P4 schedule</td>
								</tr>
								<tr class="border-b border-gray-100 dark:border-gray-700">
									<td class="py-1">1600 (good)</td>
									<td class="text-center font-mono">~270</td>
									<td>Above-average difficulty</td>
								</tr>
								<tr class="border-b border-gray-100 dark:border-gray-700">
									<td class="py-1">1700 (tough)</td>
									<td class="text-center font-mono">~330</td>
									<td>Top-tier schedule</td>
								</tr>
								<tr>
									<td class="py-1">1300 (very weak)</td>
									<td class="text-center font-mono text-red-500">-50</td>
									<td>Penalty for cupcakes</td>
								</tr>
							</tbody>
						</table>
					</div>
				</div>
			</div>
		</div>
	{/if}

	{#if expandedSection === 'confQuality'}
		<div class="card p-6 mb-8 border-l-4 border-purple-500">
			<h3 class="text-lg font-semibold text-gray-900 dark:text-white mb-4 flex items-center gap-2">
				<svg class="w-5 h-5 text-purple-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
					<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M17 20h5v-2a3 3 0 00-5.356-1.857M17 20H7m10 0v-2c0-.656-.126-1.283-.356-1.857M7 20H2v-2a3 3 0 015.356-1.857M7 20v-2c0-.656.126-1.283.356-1.857m0 0a5.002 5.002 0 019.288 0M15 7a3 3 0 11-6 0 3 3 0 016 0z" />
				</svg>
				Conference Quality — Deep Dive
			</h3>
			
			<div class="space-y-6">
				<!-- Formula -->
				<div>
					<h4 class="font-medium text-gray-900 dark:text-white mb-2">Conference Quality Formula</h4>
					<div class="bg-gray-100 dark:bg-gray-700 rounded-lg p-4 font-mono text-sm mb-3">
						CQ = RawCQ × OOC_Multiplier
					</div>
				</div>

				<!-- Raw CQ -->
				<div>
					<h4 class="font-medium text-gray-900 dark:text-white mb-2">1. Raw Conference Quality</h4>
					<p class="text-sm text-gray-600 dark:text-gray-400 mb-3">
						Average Elo of the <strong>top 50%</strong> of teams in the conference. This prevents weak bottom-feeders from dragging down strong conferences:
					</p>
					<div class="bg-purple-50 dark:bg-purple-900/20 rounded-lg p-3 text-sm">
						<span class="font-medium text-purple-700 dark:text-purple-300">Example (SEC):</span>
						<span class="text-gray-600 dark:text-gray-400"> 14 teams → Take top 7 teams' average Elo → RawCQ = 1464</span>
					</div>
				</div>

				<!-- OOC Multiplier -->
				<div>
					<h4 class="font-medium text-gray-900 dark:text-white mb-2">2. Out-of-Conference Multiplier</h4>
					<p class="text-sm text-gray-600 dark:text-gray-400 mb-3">
						Adjusts based on how the conference performs against other conferences (0.8 to 1.2 range):
					</p>
					<div class="bg-gray-100 dark:bg-gray-700 rounded-lg p-4 font-mono text-sm mb-3">
						OOC_Multiplier = 0.8 + (0.4 × PerformanceRatio)
					</div>
					<p class="text-sm text-gray-600 dark:text-gray-400 mb-3">
						Performance is weighted by opponent tier (P4 games matter most):
					</p>
					<div class="grid grid-cols-3 gap-3 text-center text-sm">
						<div class="bg-blue-50 dark:bg-blue-900/20 rounded-lg p-2">
							<div class="font-bold text-blue-600 dark:text-blue-400">1.0x</div>
							<div class="text-xs text-gray-600 dark:text-gray-400">vs Power 4</div>
						</div>
						<div class="bg-green-50 dark:bg-green-900/20 rounded-lg p-2">
							<div class="font-bold text-green-600 dark:text-green-400">0.5x</div>
							<div class="text-xs text-gray-600 dark:text-gray-400">vs Group of 5</div>
						</div>
						<div class="bg-gray-50 dark:bg-gray-700/50 rounded-lg p-2">
							<div class="font-bold text-gray-600 dark:text-gray-400">0.1x</div>
							<div class="text-xs text-gray-600 dark:text-gray-400">vs FCS</div>
						</div>
					</div>
				</div>

				<!-- Independents -->
				<div>
					<h4 class="font-medium text-gray-900 dark:text-white mb-2">FBS Independents</h4>
					<p class="text-sm text-gray-600 dark:text-gray-400">
						Teams without a conference (like Notre Dame) are assigned the <strong>average of all Power 4 Conference Quality scores</strong>, 
						treating them as elite-tier without artificial advantage.
					</p>
				</div>
			</div>
		</div>
	{/if}

	<!-- Key Features -->
	<div class="card p-6 mb-8">
		<h2 class="text-xl font-semibold text-gray-900 dark:text-white mb-4 flex items-center gap-2">
			<svg class="w-6 h-6 text-primary-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
				<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M10.325 4.317c.426-1.756 2.924-1.756 3.35 0a1.724 1.724 0 002.573 1.066c1.543-.94 3.31.826 2.37 2.37a1.724 1.724 0 001.065 2.572c1.756.426 1.756 2.924 0 3.35a1.724 1.724 0 00-1.066 2.573c.94 1.543-.826 3.31-2.37 2.37a1.724 1.724 0 00-2.572 1.065c-.426 1.756-2.924 1.756-3.35 0a1.724 1.724 0 00-2.573-1.066c-1.543.94-3.31-.826-2.37-2.37a1.724 1.724 0 00-1.065-2.572c-1.756-.426-1.756-2.924 0-3.35a1.724 1.724 0 001.066-2.573c-.94-1.543.826-3.31 2.37-2.37.996.608 2.296.07 2.572-1.065z" />
				<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" />
			</svg>
			Key Features
		</h2>
		<div class="space-y-4">
			<div class="flex gap-3">
				<div class="w-8 h-8 rounded-lg bg-amber-100 dark:bg-amber-900/30 flex items-center justify-center shrink-0">
					<span class="text-amber-600 dark:text-amber-400 font-bold text-sm">log</span>
				</div>
				<div>
					<h4 class="font-medium text-gray-900 dark:text-white">Logarithmic SoS</h4>
					<p class="text-sm text-gray-600 dark:text-gray-400">
						Strength of Schedule uses logarithmic scaling for smoother differentiation between tough and elite schedules.
					</p>
				</div>
			</div>

			<div class="flex gap-3">
				<div class="w-8 h-8 rounded-lg bg-green-100 dark:bg-green-900/30 flex items-center justify-center shrink-0">
					<svg class="w-4 h-4 text-green-600 dark:text-green-400" fill="currentColor" viewBox="0 0 20 20">
						<path d="M9.049 2.927c.3-.921 1.603-.921 1.902 0l1.07 3.292a1 1 0 00.95.69h3.462c.969 0 1.371 1.24.588 1.81l-2.8 2.034a1 1 0 00-.364 1.118l1.07 3.292c.3.921-.755 1.688-1.54 1.118l-2.8-2.034a1 1 0 00-1.175 0l-2.8 2.034c-.784.57-1.838-.197-1.539-1.118l1.07-3.292a1 1 0 00-.364-1.118L2.98 8.72c-.783-.57-.38-1.81.588-1.81h3.461a1 1 0 00.951-.69l1.07-3.292z" />
					</svg>
				</div>
				<div>
					<h4 class="font-medium text-gray-900 dark:text-white">Strength of Victory (SoV)</h4>
					<p class="text-sm text-gray-600 dark:text-gray-400">
						Bonus points awarded for defeating opponents with an Elo rating above 1200.
					</p>
				</div>
			</div>

			<div class="flex gap-3">
				<div class="w-8 h-8 rounded-lg bg-blue-100 dark:bg-blue-900/30 flex items-center justify-center shrink-0">
					<svg class="w-4 h-4 text-blue-600 dark:text-blue-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
						<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
					</svg>
				</div>
				<div>
					<h4 class="font-medium text-gray-900 dark:text-white">Reduced Legacy Bias</h4>
					<p class="text-sm text-gray-600 dark:text-gray-400">
						Historical priors blend 30% past performance with 70% fresh tier-based start (configurable). 
						Drops 3-year-old data to keep rankings current.
					</p>
				</div>
			</div>

			<div class="flex gap-3">
				<div class="w-8 h-8 rounded-lg bg-red-100 dark:bg-red-900/30 flex items-center justify-center shrink-0">
					<svg class="w-4 h-4 text-red-600 dark:text-red-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
						<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M17.657 16.657L13.414 20.9a1.998 1.998 0 01-2.827 0l-4.244-4.243a8 8 0 1111.314 0z" />
						<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 11a3 3 0 11-6 0 3 3 0 016 0z" />
					</svg>
				</div>
				<div>
					<h4 class="font-medium text-gray-900 dark:text-white">Road Warriors</h4>
					<p class="text-sm text-gray-600 dark:text-gray-400">
						Road wins are weighted 1.1x compared to home wins, rewarding teams who win away from home.
					</p>
				</div>
			</div>

			<div class="flex gap-3">
				<div class="w-8 h-8 rounded-lg bg-indigo-100 dark:bg-indigo-900/30 flex items-center justify-center shrink-0">
					<svg class="w-4 h-4 text-indigo-600 dark:text-indigo-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
						<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z" />
					</svg>
				</div>
				<div>
					<h4 class="font-medium text-gray-900 dark:text-white">Iterative Solver</h4>
					<p class="text-sm text-gray-600 dark:text-gray-400">
						The season is simulated 3 times to ensure early-season games are evaluated based on 
						end-of-season team strength, not initial assumptions.
					</p>
				</div>
			</div>
		</div>
	</div>

	<!-- Data Source -->
	<div class="card p-6">
		<h2 class="text-xl font-semibold text-gray-900 dark:text-white mb-4 flex items-center gap-2">
			<svg class="w-6 h-6 text-primary-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
				<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 7v10c0 2.21 3.582 4 8 4s8-1.79 8-4V7M4 7c0 2.21 3.582 4 8 4s8-1.79 8-4M4 7c0-2.21 3.582-4 8-4s8 1.79 8 4" />
			</svg>
			Data Source
		</h2>
		<p class="text-gray-600 dark:text-gray-400">
			All game data is sourced from the 
			<a href="https://collegefootballdata.com/" target="_blank" rel="noopener noreferrer" 
			   class="text-primary-600 dark:text-primary-400 hover:underline">
				College Football Data API
			</a>. 
			Rankings are updated after each week's games are completed.
		</p>
	</div>

	<!-- Back to Rankings -->
	<div class="mt-8 text-center">
		<a href="/" class="btn btn-primary inline-flex items-center gap-2">
			<svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
				<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M10 19l-7-7m0 0l7-7m-7 7h18" />
			</svg>
			Back to Rankings
		</a>
	</div>
</div>
