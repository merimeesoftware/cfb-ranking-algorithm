<script lang="ts">
	// Methodology page - V5.3
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
			Version 5.3 — Home Field & Quality Losses
		</p>
		<p class="mt-1 text-sm text-gray-500 dark:text-gray-500">
			Home-field advantage, quality loss credit, and G5 balance refinements
		</p>
	</div>

	<!-- Formula Card -->
	<div class="card p-6 mb-6">
		<h2 class="text-xl font-semibold text-gray-900 dark:text-white mb-4 flex items-center gap-2">
			<svg class="w-6 h-6 text-primary-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
				<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 7h6m0 10v-3m-3 3h.01M9 17h.01M9 14h.01M12 14h.01M15 11h.01M12 11h.01M9 11h.01M7 21h10a2 2 0 002-2V5a2 2 0 00-2-2H7a2 2 0 00-2 2v14a2 2 0 002 2z" />
			</svg>
			The Master Formula
		</h2>
		<div class="bg-gray-100 dark:bg-gray-700 rounded-lg p-4 font-mono text-center text-lg mb-4">
			<span class="text-primary-600 dark:text-primary-400 font-bold">FRS</span> = 
			(<span class="text-blue-600 dark:text-blue-400">0.65</span> × Team Quality) + 
			(<span class="text-green-600 dark:text-green-400">0.27</span> × Resume) + 
			(<span class="text-purple-600 dark:text-purple-400">0.08</span> × Conference Quality)
		</div>
		<p class="text-sm text-gray-600 dark:text-gray-400 text-center">
			<strong>FRS</strong> = Final Ranking Score — All components are normalized to 0-100 scale before weighting
		</p>
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
				<h3 class="font-semibold text-gray-900 dark:text-white">Team Quality (65%)</h3>
			</div>
			<p class="text-sm text-gray-600 dark:text-gray-400">
				Elo-based power rating measuring pure team strength. Uses iterative solving (2 passes), upset bonuses, 
				and tier-weighted matchups.
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

		<!-- Resume -->
		<div class="card p-5">
			<div class="flex items-center gap-3 mb-3">
				<div class="w-10 h-10 rounded-full bg-green-100 dark:bg-green-900/50 flex items-center justify-center">
					<svg class="w-5 h-5 text-green-600 dark:text-green-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
						<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2m-3 7h3m-3 4h3m-6-4h.01M9 16h.01" />
					</svg>
				</div>
				<h3 class="font-semibold text-gray-900 dark:text-white">Resume (27%)</h3>
			</div>
			<p class="text-sm text-gray-600 dark:text-gray-400">
				On-field accomplishments: win %, strength of victory, strength of schedule, milestone multipliers, 
				and relative quality win bonuses.
			</p>
			<button 
				on:click={() => toggleSection('resume')}
				class="mt-3 text-sm text-primary-600 dark:text-primary-400 hover:underline flex items-center gap-1"
			>
				{expandedSection === 'resume' ? 'Show Less' : 'Learn More'}
				<svg class="w-4 h-4 transition-transform {expandedSection === 'resume' ? 'rotate-180' : ''}" fill="none" stroke="currentColor" viewBox="0 0 24 24">
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
				<h3 class="font-semibold text-gray-900 dark:text-white">Conference Quality (8%)</h3>
			</div>
			<p class="text-sm text-gray-600 dark:text-gray-400">
				League strength contextual boost. Uses simplified formula (Mean - 0.15*StdDev) with floors.
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
				<!-- Overview -->
				<div class="bg-blue-50 dark:bg-blue-900/20 rounded-lg p-4">
					<p class="text-sm text-gray-700 dark:text-gray-300">
						<strong>What it measures:</strong> Pure team strength based on game results. Uses an Elo-based system 
						with tier-weighted matchups, upset bonuses, and iterative solving for maximum accuracy.
					</p>
				</div>

				<!-- Initial Ratings -->
				<div>
					<h4 class="font-medium text-gray-900 dark:text-white mb-2">Starting Elo Ratings by Tier</h4>
					<p class="text-sm text-gray-600 dark:text-gray-400 mb-3">
						Each team begins with a tier-based rating (85% weight) blended with their historical performance (15% weight) to reduce legacy bias while respecting pedigree:
					</p>
					<div class="grid grid-cols-3 gap-3 text-center">
						<div class="bg-blue-50 dark:bg-blue-900/30 rounded-lg p-3">
							<div class="text-2xl font-bold text-blue-600 dark:text-blue-400">1500</div>
							<div class="text-xs text-gray-600 dark:text-gray-400">Power 4</div>
							<div class="text-xs text-gray-500 dark:text-gray-500 mt-1">SEC, Big Ten, Big 12, ACC</div>
						</div>
						<div class="bg-green-50 dark:bg-green-900/30 rounded-lg p-3">
							<div class="text-2xl font-bold text-green-600 dark:text-green-400">1200</div>
							<div class="text-xs text-gray-600 dark:text-gray-400">Group of 5</div>
							<div class="text-xs text-gray-500 dark:text-gray-500 mt-1">AAC, MWC, C-USA, etc.</div>
						</div>
						<div class="bg-gray-50 dark:bg-gray-700/50 rounded-lg p-3">
							<div class="text-2xl font-bold text-gray-600 dark:text-gray-400">900</div>
							<div class="text-xs text-gray-600 dark:text-gray-400">FCS</div>
							<div class="text-xs text-gray-500 dark:text-gray-500 mt-1">Non-FBS teams</div>
						</div>
					</div>
				</div>

				<!-- Elo Update Formula -->
				<div>
					<h4 class="font-medium text-gray-900 dark:text-white mb-2">How Elo Updates Work</h4>
					<div class="bg-gray-100 dark:bg-gray-700 rounded-lg p-4 font-mono text-sm mb-3">
						Δ = K × Matchup_Weight × MoV_Factor × Upset_Bonus × (Actual - Expected)
					</div>
					<div class="space-y-2 text-sm text-gray-600 dark:text-gray-400">
						<div class="flex gap-2">
							<span class="font-medium text-gray-900 dark:text-white w-36">K-factor:</span>
							<span>Base volatility = 40. Reduced in postseason (0.6-0.7) to prevent "Bowl Bias".</span>
						</div>
						<div class="flex gap-2">
							<span class="font-medium text-gray-900 dark:text-white w-36">Expected Win:</span>
							<span>P(win) = 1 / (1 + 10^((Opp_Elo - Team_Elo) / 400))</span>
						</div>
						<div class="flex gap-2">
							<span class="font-medium text-gray-900 dark:text-white w-36">MoV Factor:</span>
							<span>log(margin + 1) — Logarithmic to prevent blowout exploitation</span>
						</div>
						<div class="flex gap-2">
							<span class="font-medium text-gray-900 dark:text-white w-36">Zero-Sum:</span>
							<span>Total Elo gained = Total Elo lost across all teams</span>
						</div>
					</div>
				</div>

				<!-- Upset Bonuses -->
				<div>
					<h4 class="font-medium text-gray-900 dark:text-white mb-2">Upset Bonuses & Chaos Tax</h4>
					<p class="text-sm text-gray-600 dark:text-gray-400 mb-3">
						Upsets receive bonus multipliers, but are subject to a global cap (1.20×) and a "Chaos Tax" in high-variance conferences:
					</p>
					<div class="grid grid-cols-3 gap-3">
						<div class="bg-yellow-50 dark:bg-yellow-900/20 rounded-lg p-3 text-center">
							<div class="text-xl font-bold text-yellow-600 dark:text-yellow-400">1.25×</div>
							<div class="text-xs text-gray-600 dark:text-gray-400">Major Upset</div>
							<div class="text-xs text-gray-500 dark:text-gray-500 mt-1">150+ Elo gap (Capped at 1.20×)</div>
						</div>
						<div class="bg-orange-50 dark:bg-orange-900/20 rounded-lg p-3 text-center">
							<div class="text-xl font-bold text-orange-600 dark:text-orange-400">1.20×</div>
							<div class="text-xs text-gray-600 dark:text-gray-400">Cross-Tier</div>
							<div class="text-xs text-gray-500 dark:text-gray-500 mt-1">G5 beats P4 team</div>
						</div>
						<div class="bg-red-50 dark:bg-red-900/20 rounded-lg p-3 text-center">
							<div class="text-xl font-bold text-red-600 dark:text-red-400">-10%</div>
							<div class="text-xs text-gray-600 dark:text-gray-400">Chaos Tax</div>
							<div class="text-xs text-gray-500 dark:text-gray-500 mt-1">0.9x dampening if StdDev > 160</div>
						</div>
					</div>
				</div>

				<!-- Matchup Weights Table -->
				<div>
					<h4 class="font-medium text-gray-900 dark:text-white mb-2">Tier Matchup Weights</h4>
					<p class="text-sm text-gray-600 dark:text-gray-400 mb-3">
						Games are weighted by tier to prevent artificial rating inflation:
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
									<td class="text-center font-mono font-bold text-blue-600 dark:text-blue-400">1.0</td>
									<td>Full weight; most competitive matchups</td>
								</tr>
								<tr class="border-b border-gray-100 dark:border-gray-700">
									<td class="py-2">P4 vs G5</td>
									<td class="text-center font-mono">0.8</td>
									<td>Reduced; expected talent gap</td>
								</tr>
								<tr class="border-b border-gray-100 dark:border-gray-700">
									<td class="py-2">G5 vs G5</td>
									<td class="text-center font-mono">0.5</td>
									<td>Dampened to prevent isolated inflation</td>
								</tr>
								<tr class="border-b border-gray-100 dark:border-gray-700">
									<td class="py-2">FBS vs FCS</td>
									<td class="text-center font-mono">0.2</td>
									<td>Minimal exchange; different divisions</td>
								</tr>
								<tr>
									<td class="py-2">FCS vs FCS</td>
									<td class="text-center font-mono text-gray-400">0.1</td>
									<td>Nearly isolated from FBS pool</td>
								</tr>
							</tbody>
						</table>
					</div>
				</div>

				<!-- Iterative Solver -->
				<div>
					<h4 class="font-medium text-gray-900 dark:text-white mb-2">2-Pass Iterative Solver</h4>
					<p class="text-sm text-gray-600 dark:text-gray-400 mb-3">
						The algorithm simulates the entire season <strong>2 times</strong> to solve the chicken-and-egg problem:
					</p>
					<div class="bg-indigo-50 dark:bg-indigo-900/20 rounded-lg p-4">
						<div class="space-y-2 text-sm text-gray-600 dark:text-gray-400">
							<div class="flex items-center gap-2">
								<span class="w-6 h-6 bg-indigo-500 text-white rounded-full flex items-center justify-center text-xs font-bold">1</span>
								<span>Initial pass with tier-based starting Elos</span>
							</div>
							<div class="flex items-center gap-2">
								<span class="w-6 h-6 bg-indigo-500 text-white rounded-full flex items-center justify-center text-xs font-bold">2</span>
								<span>Re-evaluate using Pass 1 final ratings for convergence</span>
							</div>
						</div>
						<p class="text-xs text-gray-500 dark:text-gray-500 mt-3">
							This ensures Week 1 games are fairly evaluated using end-of-season opponent strength.
						</p>
					</div>
				</div>

				<!-- Example Calculation -->
				<div>
					<h4 class="font-medium text-gray-900 dark:text-white mb-2">📊 Example: Ohio State vs Penn State</h4>
					<div class="bg-gray-50 dark:bg-gray-800 rounded-lg p-4 text-sm">
						<div class="space-y-2 text-gray-600 dark:text-gray-400">
							<div><strong>Pre-game:</strong> Ohio State (1650 Elo) vs Penn State (1580 Elo)</div>
							<div><strong>Result:</strong> Ohio State wins 28-17 (11-point margin)</div>
							<div class="mt-2 font-mono text-xs bg-gray-100 dark:bg-gray-700 p-2 rounded">
								Expected = 1 / (1 + 10^((1580-1650)/400)) = 0.60 (60% win prob)<br/>
								MoV = log(11 + 1) = 1.08<br/>
								Δ = 40 × 1.0 × 1.08 × (1.0 - 0.60) = +17.3 Elo
							</div>
							<div class="mt-2"><strong>Post-game:</strong> Ohio State → 1667 Elo, Penn State → 1563 Elo</div>
						</div>
					</div>
				</div>
			</div>
		</div>
	{/if}

	{#if expandedSection === 'resume'}
		<div class="card p-6 mb-8 border-l-4 border-green-500">
			<h3 class="text-lg font-semibold text-gray-900 dark:text-white mb-4 flex items-center gap-2">
				<svg class="w-5 h-5 text-green-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
					<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2m-3 7h3m-3 4h3m-6-4h.01M9 16h.01" />
				</svg>
				Resume — Deep Dive
			</h3>
			
			<div class="space-y-6">
				<!-- Overview -->
				<div class="bg-green-50 dark:bg-green-900/20 rounded-lg p-4">
					<p class="text-sm text-gray-700 dark:text-gray-300">
						<strong>What it measures:</strong> On-field accomplishments — wins, quality of opponents beaten, 
						strength of schedule, head-to-head results, and momentum. This component answers "What have you actually done?"
					</p>
				</div>

				<!-- Master Formula -->
				<div>
					<h4 class="font-medium text-gray-900 dark:text-white mb-2">Resume Score Formula</h4>
					<div class="bg-gray-100 dark:bg-gray-700 rounded-lg p-4 font-mono text-xs mb-3 overflow-x-auto">
						Resume = (Base + WeightedWinPct + SoV + SoS - BadLoss + QW) × MilestoneMultiplier
					</div>
					<p class="text-sm text-gray-600 dark:text-gray-400">
						All components are calculated then normalized to 0-100 scale.
					</p>
				</div>

				<!-- Component Grid -->
				<div class="grid md:grid-cols-2 gap-4">
					<!-- Weighted Win % -->
					<div class="bg-gray-50 dark:bg-gray-800 rounded-lg p-4">
						<h5 class="font-medium text-gray-900 dark:text-white mb-2 flex items-center gap-2">
							<span class="w-5 h-5 bg-green-500 text-white rounded text-xs flex items-center justify-center font-bold">1</span>
							Weighted Win Percentage
						</h5>
						<div class="text-sm text-gray-600 dark:text-gray-400 mb-2">
							Road wins count 10% more than home wins:
						</div>
						<div class="font-mono text-xs bg-gray-100 dark:bg-gray-700 p-2 rounded">
							WinPct = (HomeW×1.0 + RoadW×1.1) / Games
						</div>
					</div>

					<!-- Milestones -->
					<div class="bg-gray-50 dark:bg-gray-800 rounded-lg p-4">
						<h5 class="font-medium text-gray-900 dark:text-white mb-2 flex items-center gap-2">
							<span class="w-5 h-5 bg-green-500 text-white rounded text-xs flex items-center justify-center font-bold">2</span>
							Milestone Multiplier & Anchor
						</h5>
						<div class="text-sm text-gray-600 dark:text-gray-400 mb-2">
							Multiplicative boost + additive anchor for elite achievements:
						</div>
						<div class="font-mono text-xs bg-gray-100 dark:bg-gray-700 p-2 rounded space-y-1">
							<div>Undefeated: +5% (1.05x)</div>
							<div>Conf Champ: +7% (1.07x) + 140 pts</div>
							<div>Champ App: +3% (1.03x) + 70 pts</div>
						</div>
					</div>

					<!-- SoS -->
					<div class="bg-gray-50 dark:bg-gray-800 rounded-lg p-4">
						<h5 class="font-medium text-gray-900 dark:text-white mb-2 flex items-center gap-2">
							<span class="w-5 h-5 bg-green-500 text-white rounded text-xs flex items-center justify-center font-bold">3</span>
							Strength of Schedule (SoS)
						</h5>
						<div class="text-sm text-gray-600 dark:text-gray-400 mb-2">
							Logarithmic reward for tough schedules (tier-specific):
						</div>
						<div class="font-mono text-xs bg-gray-100 dark:bg-gray-700 p-2 rounded">
							P4: base 1400 | G5: base 1300
						</div>
					</div>

					<!-- Bad Loss Penalty -->
					<div class="bg-gray-50 dark:bg-gray-800 rounded-lg p-4">
						<h5 class="font-medium text-gray-900 dark:text-white mb-2 flex items-center gap-2">
							<span class="w-5 h-5 bg-red-500 text-white rounded text-xs flex items-center justify-center font-bold">4</span>
							Bad Loss Penalty
						</h5>
						<div class="text-sm text-gray-600 dark:text-gray-400 mb-2">
						Penalizes losses to Bottom 25% opponents (Relative Threshold).
					</div>
					<div class="font-mono text-xs bg-gray-100 dark:bg-gray-700 p-2 rounded">
						Penalty = (Threshold - OppElo) × 0.5<br/>
						<span class="text-gray-500 italic">Relative threshold ensures fairness</span>
						</div>
					</div>
				</div>

				<!-- Bonus Components -->
				<div>
					<h4 class="font-medium text-gray-900 dark:text-white mb-3">Bonus Components</h4>
					<div class="space-y-3">
						<!-- Quality Win -->
						<div class="flex items-start gap-3 bg-blue-50 dark:bg-blue-900/20 rounded-lg p-3">
							<span class="w-8 h-8 bg-blue-500 text-white rounded-lg flex items-center justify-center text-sm font-bold shrink-0">QW</span>
							<div>
								<h5 class="font-medium text-gray-900 dark:text-white">Quality Win Bonus</h5>
								<p class="text-sm text-gray-600 dark:text-gray-400">
									Bonus for beating Top 20% caliber teams (Relative Threshold).
								</p>
								<div class="font-mono text-xs bg-gray-100 dark:bg-gray-700 p-2 rounded mt-2">
									QW = (OppElo - Threshold) × 0.50
								</div>
							</div>
						</div>
					</div>
				</div>

				<!-- Example Calculation -->
				<div>
					<h4 class="font-medium text-gray-900 dark:text-white mb-2">📊 Example: 10-2 Power 4 Team</h4>
					<div class="bg-gray-50 dark:bg-gray-800 rounded-lg p-4 text-sm">
						<div class="space-y-2 text-gray-600 dark:text-gray-400">
							<div><strong>Record:</strong> 10-2 (6 home wins, 4 road wins)</div>
							<div><strong>Avg Win Elo:</strong> 1450 | <strong>Avg Opp Elo:</strong> 1520</div>
							<div><strong>Context:</strong> Beat 2 teams with equal record, lost to #3 team (1680 Elo)</div>
							<div class="mt-3 font-mono text-xs bg-gray-100 dark:bg-gray-700 p-3 rounded space-y-1">
								<div>Base: 1000</div>
								<div>WinPct: (6×1.0 + 4×1.1) / 12 = 0.87 → +867</div>
								<div>SoV: (1450 - 1200) × 0.25 = +62</div>
								<div>SoS: (1520 - 1400) × 2.0 = +240</div>
								<div>Win Count Bonus: (10 - 9) × 20 = +20</div>
								<div>BadLoss: 0 (Loss was to stronger team)</div>
								<div>QL: (1680 - 1600) × 0.165 = +13</div>
								<div class="border-t border-gray-300 dark:border-gray-600 pt-1 mt-1 font-bold">
									Total: 2202 → Normalized to ~72/100
								</div>
							</div>
						</div>
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
				<!-- Overview -->
				<div class="bg-purple-50 dark:bg-purple-900/20 rounded-lg p-4">
					<p class="text-sm text-gray-700 dark:text-gray-300">
						<strong>What it measures:</strong> The overall strength of a team's conference, providing contextual credit 
						for playing in tougher leagues. A 9-3 record in the SEC means more than 9-3 in a weak conference.
					</p>
				</div>

				<!-- Hybrid Formula -->
				<div>
					<h4 class="font-medium text-gray-900 dark:text-white mb-2">Simplified Formula</h4>
					<div class="bg-gray-100 dark:bg-gray-700 rounded-lg p-4 font-mono text-sm mb-3">
						CQ = Mean_Elo - (0.15 × StdDev)
					</div>
					<p class="text-sm text-gray-600 dark:text-gray-400">
						This formula rewards high average strength while penalizing extreme variance (cannibalization).
						Floors are applied (P4=1400, G5=1250) to ensure baseline respect.
						<br/><span class="text-xs italic mt-1 block">Note: SEC receives a +20.0 depth adjustment.</span>
					</p>
				</div>

				<!-- Visual Breakdown -->
				<div>
					<h4 class="font-medium text-gray-900 dark:text-white mb-2">Why StdDev Penalty?</h4>
					<div class="grid md:grid-cols-2 gap-4">
						<div class="bg-purple-50 dark:bg-purple-900/20 rounded-lg p-4">
							<h5 class="font-medium text-purple-700 dark:text-purple-300 mb-2">Mean Elo</h5>
							<p class="text-sm text-gray-600 dark:text-gray-400">
								The primary driver. A conference with higher average team strength is tougher to play in.
							</p>
						</div>
						<div class="bg-gray-50 dark:bg-gray-700/50 rounded-lg p-4">
							<h5 class="font-medium text-gray-700 dark:text-gray-300 mb-2">StdDev Penalty</h5>
							<p class="text-sm text-gray-600 dark:text-gray-400">
								High variance implies a "top-heavy" league with many weak teams. Low variance implies depth.
								We penalize high variance to reward depth.
							</p>
						</div>
					</div>
				</div>

				<!-- Independents -->
				<div>
					<h4 class="font-medium text-gray-900 dark:text-white mb-2">FBS Independents</h4>
					<div class="bg-indigo-50 dark:bg-indigo-900/20 rounded-lg p-4">
						<p class="text-sm text-gray-600 dark:text-gray-400">
							Teams without a conference (Notre Dame, UConn, UMass) receive a <strong>Synthetic Conference Quality</strong> score. 
							This is calculated as the average CQ of all the conferences on their schedule. If they play a P4 schedule, they get a P4 boost; 
							if they play a G5 schedule, they get a G5 boost.
						</p>
					</div>
				</div>

				<!-- Example -->
				<div>
					<h4 class="font-medium text-gray-900 dark:text-white mb-2">📊 Example: SEC Conference</h4>
					<div class="bg-gray-50 dark:bg-gray-800 rounded-lg p-4 text-sm">
						<div class="space-y-2 text-gray-600 dark:text-gray-400">
							<div><strong>Teams:</strong> 16 teams (Top 8 avg Elo: 1520, Full avg Elo: 1420)</div>
							<div><strong>OOC Record vs P4:</strong> 12-4 (0.75 win rate)</div>
							<div class="mt-3 font-mono text-xs bg-gray-100 dark:bg-gray-700 p-3 rounded space-y-1">
								<div>RawCQ = (0.70 × 1520) + (0.30 × 1420) = 1490</div>
								<div>OOC_Perf = 0.75 → Multiplier = 1.10</div>
								<div class="border-t border-gray-300 dark:border-gray-600 pt-1 mt-1 font-bold">
									FinalCQ = 1490 × 1.10 = 1639 → Normalized to ~85/100
								</div>
							</div>
						</div>
					</div>
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
			Key Features of V5.3
		</h2>
		
		<!-- Feature Grid -->
		<div class="grid md:grid-cols-2 gap-4 mb-6">
			<!-- Iterative Solver -->
			<div class="flex gap-3 p-4 bg-indigo-50 dark:bg-indigo-900/20 rounded-lg">
				<div class="w-10 h-10 rounded-lg bg-indigo-500 flex items-center justify-center shrink-0">
					<svg class="w-5 h-5 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
						<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
					</svg>
				</div>
				<div>
					<h4 class="font-medium text-gray-900 dark:text-white">2-Pass Iterative Solver</h4>
					<p class="text-sm text-gray-600 dark:text-gray-400">
						Re-simulates the entire season 2 times so Week 1 games are evaluated with end-of-season opponent strength data.
					</p>
				</div>
			</div>

			<!-- Zero-Sum Elo -->
			<div class="flex gap-3 p-4 bg-blue-50 dark:bg-blue-900/20 rounded-lg">
				<div class="w-10 h-10 rounded-lg bg-blue-500 flex items-center justify-center shrink-0">
					<svg class="w-5 h-5 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
						<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M3 6l3 1m0 0l-3 9a5.002 5.002 0 006.001 0M6 7l3 9M6 7l6-2m6 2l3-1m-3 1l-3 9a5.002 5.002 0 006.001 0M18 7l3 9m-3-9l-6-2m0-2v2m0 16V5m0 16H9m3 0h3" />
					</svg>
				</div>
				<div>
					<h4 class="font-medium text-gray-900 dark:text-white">Zero-Sum Elo</h4>
					<p class="text-sm text-gray-600 dark:text-gray-400">
						Total Elo gained always equals total Elo lost. No artificial inflation — every point earned is a point taken from an opponent.
					</p>
				</div>
			</div>

			<!-- Milestone Multiplier -->
			<div class="flex gap-3 p-4 bg-green-50 dark:bg-green-900/20 rounded-lg">
				<div class="w-10 h-10 rounded-lg bg-green-500 flex items-center justify-center shrink-0">
					<svg class="w-5 h-5 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
						<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M5 3v4M3 5h4M6 17v4m-2-2h4m5-16l2.286 6.857L21 12l-5.714 2.143L13 21l-2.286-6.857L5 12l5.714-2.143L13 3z" />
					</svg>
				</div>
				<div>
					<h4 class="font-medium text-gray-900 dark:text-white">Milestone Anchors</h4>
					<p class="text-sm text-gray-600 dark:text-gray-400">
						Champions get a massive boost (1.07x + 140pts). This "anchor" ensures conference winners rise to the top.
					</p>
				</div>
			</div>

			<!-- Relative Thresholds -->
			<div class="flex gap-3 p-4 bg-purple-50 dark:bg-purple-900/20 rounded-lg">
				<div class="w-10 h-10 rounded-lg bg-purple-500 flex items-center justify-center shrink-0">
					<svg class="w-5 h-5 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
						<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z" />
					</svg>
				</div>
				<div>
					<h4 class="font-medium text-gray-900 dark:text-white">Relative Thresholds</h4>
					<p class="text-sm text-gray-600 dark:text-gray-400">
						Quality Wins and Bad Losses are defined by dynamic percentiles (Top 20% / Bottom 25%) rather than fixed numbers.
					</p>
				</div>
			</div>

			<!-- Logarithmic MoV -->
			<div class="flex gap-3 p-4 bg-amber-50 dark:bg-amber-900/20 rounded-lg">
				<div class="w-10 h-10 rounded-lg bg-amber-500 flex items-center justify-center shrink-0">
					<span class="text-white font-bold text-sm">log</span>
				</div>
				<div>
					<h4 class="font-medium text-gray-900 dark:text-white">Logarithmic Margin of Victory</h4>
					<p class="text-sm text-gray-600 dark:text-gray-400">
						Uses log(margin + 1) to prevent blowout exploitation. Winning 42-7 isn't worth much more than 28-7.
					</p>
				</div>
			</div>

			<!-- Road Warrior -->
			<div class="flex gap-3 p-4 bg-red-50 dark:bg-red-900/20 rounded-lg">
				<div class="w-10 h-10 rounded-lg bg-red-500 flex items-center justify-center shrink-0">
					<svg class="w-5 h-5 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
						<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M17.657 16.657L13.414 20.9a1.998 1.998 0 01-2.827 0l-4.244-4.243a8 8 0 1111.314 0z" />
						<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 11a3 3 0 11-6 0 3 3 0 016 0z" />
					</svg>
				</div>
				<div>
					<h4 class="font-medium text-gray-900 dark:text-white">Road Warrior Bonus</h4>
					<p class="text-sm text-gray-600 dark:text-gray-400">
						Road wins count 1.1× in Resume calculations. Winning in hostile environments deserves extra credit.
					</p>
				</div>
			</div>
		</div>

		<!-- Additional Features List -->
		<div class="border-t border-gray-200 dark:border-gray-700 pt-4">
			<h4 class="font-medium text-gray-900 dark:text-white mb-3">Additional V5.3 Innovations</h4>
			<div class="grid md:grid-cols-2 gap-3 text-sm">
				<div class="flex items-center gap-2 text-gray-600 dark:text-gray-400">
					<svg class="w-4 h-4 text-green-500 shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24">
						<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M5 13l4 4L19 7" />
					</svg>
					<span><strong>Home-Field Advantage:</strong> 65 Elo bonus for home team expectation</span>
				</div>
				<div class="flex items-center gap-2 text-gray-600 dark:text-gray-400">
					<svg class="w-4 h-4 text-green-500 shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24">
						<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M5 13l4 4L19 7" />
					</svg>
					<span><strong>Elo Clamp:</strong> Ratings capped at 1850 to prevent outliers</span>
				</div>
				<div class="flex items-center gap-2 text-gray-600 dark:text-gray-400">
					<svg class="w-4 h-4 text-green-500 shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24">
						<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M5 13l4 4L19 7" />
					</svg>
					<span><strong>Postseason K Reduction:</strong> 0.65× K-factor for bowl games</span>
				</div>
				<div class="flex items-center gap-2 text-gray-600 dark:text-gray-400">
					<svg class="w-4 h-4 text-green-500 shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24">
						<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M5 13l4 4L19 7" />
					</svg>
					<span><strong>Chaos Tax:</strong> 10% CQ penalty if conference StdDev > 160</span>
				</div>
				<div class="flex items-center gap-2 text-gray-600 dark:text-gray-400">
					<svg class="w-4 h-4 text-green-500 shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24">
						<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M5 13l4 4L19 7" />
					</svg>
					<span><strong>Quality Loss Bonus:</strong> Credit for losses to Top 20% teams</span>
				</div>
				<div class="flex items-center gap-2 text-gray-600 dark:text-gray-400">
					<svg class="w-4 h-4 text-green-500 shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24">
						<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M5 13l4 4L19 7" />
					</svg>
					<span><strong>Bad Loss Penalty:</strong> Penalty for losses to Bottom 25% teams</span>
				</div>
				<div class="flex items-center gap-2 text-gray-600 dark:text-gray-400">
					<svg class="w-4 h-4 text-green-500 shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24">
						<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M5 13l4 4L19 7" />
					</svg>
					<span><strong>Perfection Bonus:</strong> 5% for undefeated, 2% for one-loss</span>
				</div>
				<div class="flex items-center gap-2 text-gray-600 dark:text-gray-400">
					<svg class="w-4 h-4 text-green-500 shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24">
						<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M5 13l4 4L19 7" />
					</svg>
					<span><strong>Synthetic Indie CQ:</strong> Schedule-weighted CQ for independents</span>
				</div>
			</div>
		</div>
	</div>

	<!-- Philosophy Section -->
	<div class="card p-6 mb-8 bg-gradient-to-br from-primary-50 to-blue-50 dark:from-gray-800 dark:to-gray-800 border-primary-200 dark:border-gray-600">
		<h2 class="text-xl font-semibold text-gray-900 dark:text-white mb-4 flex items-center gap-2">
			<svg class="w-6 h-6 text-primary-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
				<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9.663 17h4.673M12 3v1m6.364 1.636l-.707.707M21 12h-1M4 12H3m3.343-5.657l-.707-.707m2.828 9.9a5 5 0 117.072 0l-.548.547A3.374 3.374 0 0014 18.469V19a2 2 0 11-4 0v-.531c0-.895-.356-1.754-.988-2.386l-.548-.547z" />
			</svg>
			Design Philosophy
		</h2>
		<div class="space-y-4">
			<div class="flex gap-4">
				<div class="w-1 bg-primary-500 rounded-full shrink-0"></div>
				<div>
					<h4 class="font-medium text-gray-900 dark:text-white">Balance Power & Resume</h4>
					<p class="text-sm text-gray-600 dark:text-gray-400">
						Team Quality (65%) answers "How good are you?" while Resume (27%) answers "What have you actually done?" 
						Neither pure predictive nor pure résumé — a hybrid that rewards both.
					</p>
				</div>
			</div>
			<div class="flex gap-4">
				<div class="w-1 bg-primary-500 rounded-full shrink-0"></div>
				<div>
					<h4 class="font-medium text-gray-900 dark:text-white">Fair Cross-Tier Evaluation</h4>
					<p class="text-sm text-gray-600 dark:text-gray-400">
						G5 teams aren't penalized for their conference but must prove themselves through SoS, cross-tier wins, 
						and scheduling. The best G5 teams can crack the Top 15.
					</p>
				</div>
			</div>
			<div class="flex gap-4">
				<div class="w-1 bg-primary-500 rounded-full shrink-0"></div>
				<div>
					<h4 class="font-medium text-gray-900 dark:text-white">Recency Without Recency Bias</h4>
					<p class="text-sm text-gray-600 dark:text-gray-400">
						Early-season games are re-evaluated fairly through iterative solving. 
						No artificial late-season boost or "eye test" bias.
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
