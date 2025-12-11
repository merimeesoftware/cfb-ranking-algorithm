<script lang="ts">
	// Methodology page - V4.0
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
			Version 4.5 — Resume Emphasis
		</p>
		<p class="mt-1 text-sm text-gray-500 dark:text-gray-500">
			A hybrid system balancing pure team strength with on-field accomplishments
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
			(<span class="text-blue-600 dark:text-blue-400">0.50</span> × Team Quality) + 
			(<span class="text-green-600 dark:text-green-400">0.42</span> × Resume) + 
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
				<h3 class="font-semibold text-gray-900 dark:text-white">Team Quality (50%)</h3>
			</div>
			<p class="text-sm text-gray-600 dark:text-gray-400">
				Elo-based power rating measuring pure team strength. Uses iterative solving, upset bonuses, 
				and tier-weighted matchups for accuracy.
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
				<h3 class="font-semibold text-gray-900 dark:text-white">Resume (42%)</h3>
			</div>
			<p class="text-sm text-gray-600 dark:text-gray-400">
				On-field accomplishments: win %, strength of victory, strength of schedule, head-to-head results, 
				bad loss penalty, and quality win bonuses.
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
				League strength contextual boost. Uses hybrid formula (70% top-half, 30% full) with depth adjustment and OOC multiplier.
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
					<h4 class="font-medium text-gray-900 dark:text-white mb-2">Upset Bonuses</h4>
					<p class="text-sm text-gray-600 dark:text-gray-400 mb-3">
						Upsets receive bonus multipliers to properly reward unexpected victories:
					</p>
					<div class="grid grid-cols-2 gap-3">
						<div class="bg-yellow-50 dark:bg-yellow-900/20 rounded-lg p-3 text-center">
							<div class="text-xl font-bold text-yellow-600 dark:text-yellow-400">1.25×</div>
							<div class="text-xs text-gray-600 dark:text-gray-400">Major Upset</div>
							<div class="text-xs text-gray-500 dark:text-gray-500 mt-1">150+ Elo gap overcome</div>
						</div>
						<div class="bg-orange-50 dark:bg-orange-900/20 rounded-lg p-3 text-center">
							<div class="text-xl font-bold text-orange-600 dark:text-orange-400">1.20×</div>
							<div class="text-xs text-gray-600 dark:text-gray-400">Cross-Tier Upset</div>
							<div class="text-xs text-gray-500 dark:text-gray-500 mt-1">G5 beats P4 team</div>
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
					<h4 class="font-medium text-gray-900 dark:text-white mb-2">4-Pass Iterative Solver</h4>
					<p class="text-sm text-gray-600 dark:text-gray-400 mb-3">
						The algorithm simulates the entire season <strong>4 times</strong> to solve the chicken-and-egg problem:
					</p>
					<div class="bg-indigo-50 dark:bg-indigo-900/20 rounded-lg p-4">
						<div class="space-y-2 text-sm text-gray-600 dark:text-gray-400">
							<div class="flex items-center gap-2">
								<span class="w-6 h-6 bg-indigo-500 text-white rounded-full flex items-center justify-center text-xs font-bold">1</span>
								<span>Initial pass with tier-based starting Elos</span>
							</div>
							<div class="flex items-center gap-2">
								<span class="w-6 h-6 bg-indigo-500 text-white rounded-full flex items-center justify-center text-xs font-bold">2</span>
								<span>Re-evaluate using Pass 1 final ratings</span>
							</div>
							<div class="flex items-center gap-2">
								<span class="w-6 h-6 bg-indigo-500 text-white rounded-full flex items-center justify-center text-xs font-bold">3</span>
								<span>Refine with improved opponent strength data</span>
							</div>
							<div class="flex items-center gap-2">
								<span class="w-6 h-6 bg-indigo-500 text-white rounded-full flex items-center justify-center text-xs font-bold">4</span>
								<span>Final pass for convergence</span>
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
						Resume = Base + WeightedWinPct + SoV + SoS - BadLoss + H2H + QL + QW - BadWin + CrossTier
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

					<!-- SoV -->
					<div class="bg-gray-50 dark:bg-gray-800 rounded-lg p-4">
						<h5 class="font-medium text-gray-900 dark:text-white mb-2 flex items-center gap-2">
							<span class="w-5 h-5 bg-green-500 text-white rounded text-xs flex items-center justify-center font-bold">2</span>
							Strength of Victory (SoV)
						</h5>
						<div class="text-sm text-gray-600 dark:text-gray-400 mb-2">
							Bonus for beating quality opponents (tier-specific thresholds):
						</div>
						<div class="font-mono text-xs bg-gray-100 dark:bg-gray-700 p-2 rounded">
							P4: threshold 1200 | G5: threshold 1050
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
							P4: base 1420 | G5: base 1300
						</div>
					</div>

					<!-- Bad Loss Penalty -->
					<div class="bg-gray-50 dark:bg-gray-800 rounded-lg p-4">
						<h5 class="font-medium text-gray-900 dark:text-white mb-2 flex items-center gap-2">
							<span class="w-5 h-5 bg-red-500 text-white rounded text-xs flex items-center justify-center font-bold">4</span>
							Bad Loss Penalty
						</h5>
						<div class="text-sm text-gray-600 dark:text-gray-400 mb-2">
						Penalizes losses to significantly weaker opponents (Elo gap > 200) OR blowout losses (21+ pts) to similar/weaker teams:
					</div>
					<div class="font-mono text-xs bg-gray-100 dark:bg-gray-700 p-2 rounded">
						Penalty = (TeamElo - OppElo - 200) × 0.15<br/>
						<span class="text-gray-500 italic">OR</span><br/>
						Penalty = 10 + (MoV - 21) × 1.0 <span class="text-gray-500">(if blowout)</span><br/>
						<span class="text-gray-500 italic">OR</span><br/>
						Penalty = (gap - 150) × 0.08 + (MoV - 21) × 0.5 <span class="text-gray-500">(minor: 150-200 gap + blowout)</span>
						</div>
					</div>
				</div>

				<!-- Bonus Components -->
				<div>
					<h4 class="font-medium text-gray-900 dark:text-white mb-3">Bonus Components</h4>
					<div class="space-y-3">
						<!-- H2H -->
						<div class="flex items-start gap-3 bg-yellow-50 dark:bg-yellow-900/20 rounded-lg p-3">
							<span class="w-8 h-8 bg-yellow-500 text-white rounded-lg flex items-center justify-center text-sm font-bold shrink-0">H2H</span>
							<div>
								<h5 class="font-medium text-gray-900 dark:text-white">Head-to-Head Bonus</h5>
								<p class="text-sm text-gray-600 dark:text-gray-400">
									+88 points for Top 10 wins, +44 for Top 25 wins. Rewards beating the best.
								</p>
							</div>
						</div>

						<!-- Quality Loss -->
						<div class="flex items-start gap-3 bg-purple-50 dark:bg-purple-900/20 rounded-lg p-3">
							<span class="w-8 h-8 bg-purple-500 text-white rounded-lg flex items-center justify-center text-sm font-bold shrink-0">QL</span>
							<div>
								<h5 class="font-medium text-gray-900 dark:text-white">Quality Loss Bonus</h5>
								<p class="text-sm text-gray-600 dark:text-gray-400">
									Partial credit for competitive losses to elite teams (Elo > 1600).
								</p>
								<div class="font-mono text-xs bg-gray-100 dark:bg-gray-700 p-2 rounded mt-2">
									QL = (OppElo - 1600) × 0.165 <span class="text-gray-500">[Max 33 pts]</span>
								</div>
							</div>
						</div>

						<!-- Quality Win -->
						<div class="flex items-start gap-3 bg-blue-50 dark:bg-blue-900/20 rounded-lg p-3">
							<span class="w-8 h-8 bg-blue-500 text-white rounded-lg flex items-center justify-center text-sm font-bold shrink-0">QW</span>
							<div>
								<h5 class="font-medium text-gray-900 dark:text-white">Quality Win Bonus</h5>
								<p class="text-sm text-gray-600 dark:text-gray-400">
									Bonus for beating significantly stronger opponents (Elo gap > 100).
								</p>
								<div class="font-mono text-xs bg-gray-100 dark:bg-gray-700 p-2 rounded mt-2">
									QW = (OppElo - TeamElo) × 0.08 <span class="text-gray-500">[Max 50 pts]</span>
								</div>
							</div>
						</div>

						<!-- Bad Win Penalty -->
						<div class="flex items-start gap-3 bg-red-50 dark:bg-red-900/20 rounded-lg p-3">
							<span class="w-8 h-8 bg-red-500 text-white rounded-lg flex items-center justify-center text-sm font-bold shrink-0">BW</span>
							<div>
								<h5 class="font-medium text-gray-900 dark:text-white">Bad Win Penalty</h5>
								<p class="text-sm text-gray-600 dark:text-gray-400">
									Penalty for close wins (≤7 pts) against significantly weaker opponents (Elo gap > 100).
								</p>
								<div class="font-mono text-xs bg-gray-100 dark:bg-gray-700 p-2 rounded mt-2">
									BW = 20 + (7 - MoV) × 2 <span class="text-gray-500">[Max 50 pts]</span>
								</div>
							</div>
						</div>

						<!-- Cross-Tier -->
						<div class="flex items-start gap-3 bg-orange-50 dark:bg-orange-900/20 rounded-lg p-3">
							<span class="w-8 h-8 bg-orange-500 text-white rounded-lg flex items-center justify-center text-sm font-bold shrink-0">CT</span>
							<div>
								<h5 class="font-medium text-gray-900 dark:text-white">Cross-Tier Bonus (G5 only)</h5>
								<p class="text-sm text-gray-600 dark:text-gray-400">
									+80 points per P4 win for G5 teams. Rewards scheduling up and winning.
								</p>
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
								<div>SoV: (1450 - 1200) × 0.35 = +88</div>
								<div>SoS: log(1520 - 1420) × 80 = +368</div>
								<div>BadLoss: 0 (Loss was to stronger team)</div>
								<div>H2H: 2 × 44 = +88</div>
								<div>QL: (1680 - 1600) × 0.165 = +13</div>
								<div class="border-t border-gray-300 dark:border-gray-600 pt-1 mt-1 font-bold">
									Total: 2424 → Normalized to ~78/100
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
					<h4 class="font-medium text-gray-900 dark:text-white mb-2">Hybrid Conference Quality Formula</h4>
					<div class="bg-gray-100 dark:bg-gray-700 rounded-lg p-4 font-mono text-sm mb-3">
						RawCQ = (0.70 × TopHalfAvg) + (0.30 × FullAvg) + DepthAdj - BadLossAgg
					</div>
					<p class="text-sm text-gray-600 dark:text-gray-400">
						This hybrid approach weights the top half of the conference more heavily (70%) while still 
						considering the full conference average (30%). It also rewards depth (low variance) and penalizes 
						conferences with many bad losses.
					</p>
				</div>

				<!-- Visual Breakdown -->
				<div>
					<h4 class="font-medium text-gray-900 dark:text-white mb-2">Why 70/30 Split?</h4>
					<div class="grid md:grid-cols-2 gap-4">
						<div class="bg-purple-50 dark:bg-purple-900/20 rounded-lg p-4">
							<h5 class="font-medium text-purple-700 dark:text-purple-300 mb-2">Top Half (70%)</h5>
							<p class="text-sm text-gray-600 dark:text-gray-400">
								The teams you're most likely to compete against for conference championships and playoff spots. 
								These are the meaningful games.
							</p>
						</div>
						<div class="bg-gray-50 dark:bg-gray-700/50 rounded-lg p-4">
							<h5 class="font-medium text-gray-700 dark:text-gray-300 mb-2">Full Average (30%)</h5>
							<p class="text-sm text-gray-600 dark:text-gray-400">
								Accounts for conference depth. A conference with a weak bottom half should be slightly penalized, 
								but not dramatically.
							</p>
						</div>
					</div>
				</div>

				<!-- OOC Multiplier -->
				<div>
					<h4 class="font-medium text-gray-900 dark:text-white mb-2">Out-of-Conference Performance Multiplier</h4>
					<div class="bg-gray-100 dark:bg-gray-700 rounded-lg p-4 font-mono text-sm mb-3">
						FinalCQ = RawCQ × OOC_Multiplier<br/>
						<span class="text-gray-500">where OOC_Multiplier ranges from 0.80 to 1.20</span>
					</div>
					<p class="text-sm text-gray-600 dark:text-gray-400 mb-3">
						The OOC multiplier adjusts conference quality based on how the conference performs against other conferences:
					</p>
					<div class="grid grid-cols-3 gap-3 text-center text-sm">
						<div class="bg-red-50 dark:bg-red-900/20 rounded-lg p-3">
							<div class="text-xl font-bold text-red-600 dark:text-red-400">0.80×</div>
							<div class="text-xs text-gray-600 dark:text-gray-400">Underperforming</div>
							<div class="text-xs text-gray-500 dark:text-gray-500 mt-1">Losing OOC games</div>
						</div>
						<div class="bg-gray-50 dark:bg-gray-700/50 rounded-lg p-3">
							<div class="text-xl font-bold text-gray-600 dark:text-gray-400">1.00×</div>
							<div class="text-xs text-gray-600 dark:text-gray-400">Neutral</div>
							<div class="text-xs text-gray-500 dark:text-gray-500 mt-1">Meeting expectations</div>
						</div>
						<div class="bg-green-50 dark:bg-green-900/20 rounded-lg p-3">
							<div class="text-xl font-bold text-green-600 dark:text-green-400">1.20×</div>
							<div class="text-xs text-gray-600 dark:text-gray-400">Dominant</div>
							<div class="text-xs text-gray-500 dark:text-gray-500 mt-1">Winning OOC games</div>
						</div>
					</div>
				</div>

				<!-- OOC Weights -->
				<div>
					<h4 class="font-medium text-gray-900 dark:text-white mb-2">OOC Opponent Tier Weights</h4>
					<p class="text-sm text-gray-600 dark:text-gray-400 mb-3">
						Not all OOC games count equally — beating P4 teams matters most:
					</p>
					<div class="grid grid-cols-3 gap-3 text-center text-sm">
						<div class="bg-blue-50 dark:bg-blue-900/20 rounded-lg p-2">
							<div class="font-bold text-blue-600 dark:text-blue-400">1.2×</div>
							<div class="text-xs text-gray-600 dark:text-gray-400">vs Power 4</div>
						</div>
						<div class="bg-green-50 dark:bg-green-900/20 rounded-lg p-2">
							<div class="font-bold text-green-600 dark:text-green-400">0.5×</div>
							<div class="text-xs text-gray-600 dark:text-gray-400">vs Group of 5</div>
						</div>
						<div class="bg-gray-50 dark:bg-gray-700/50 rounded-lg p-2">
							<div class="font-bold text-gray-600 dark:text-gray-400">0.1×</div>
							<div class="text-xs text-gray-600 dark:text-gray-400">vs FCS</div>
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
			Key Features of V4.5
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
					<h4 class="font-medium text-gray-900 dark:text-white">4-Pass Iterative Solver</h4>
					<p class="text-sm text-gray-600 dark:text-gray-400">
						Re-simulates the entire season 4 times so Week 1 games are evaluated with end-of-season opponent strength data. Eliminates early-season guesswork.
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

			<!-- Upset Bonuses -->
			<div class="flex gap-3 p-4 bg-yellow-50 dark:bg-yellow-900/20 rounded-lg">
				<div class="w-10 h-10 rounded-lg bg-yellow-500 flex items-center justify-center shrink-0">
					<svg class="w-5 h-5 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
						<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13 10V3L4 14h7v7l9-11h-7z" />
					</svg>
				</div>
				<div>
					<h4 class="font-medium text-gray-900 dark:text-white">Upset Bonuses</h4>
					<p class="text-sm text-gray-600 dark:text-gray-400">
						Upsets receive 1.25× multiplier for major upsets (150+ Elo gap) and 1.20× for G5 teams beating P4 opponents. Rewards playing up.
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
						Uses log(margin + 1) to prevent blowout exploitation. Winning 42-7 isn't worth much more than 28-7 — but it's still better.
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

			<!-- Tier-Specific Thresholds -->
			<div class="flex gap-3 p-4 bg-green-50 dark:bg-green-900/20 rounded-lg">
				<div class="w-10 h-10 rounded-lg bg-green-500 flex items-center justify-center shrink-0">
					<svg class="w-5 h-5 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
						<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z" />
					</svg>
				</div>
				<div>
					<h4 class="font-medium text-gray-900 dark:text-white">Tier-Specific Thresholds</h4>
					<p class="text-sm text-gray-600 dark:text-gray-400">
						G5 teams have adjusted thresholds for SoV (1050 vs 1200) and SoS (1300 vs 1400). Fair comparisons within tier.
					</p>
				</div>
			</div>
		</div>

		<!-- Additional Features List -->
		<div class="border-t border-gray-200 dark:border-gray-700 pt-4">
			<h4 class="font-medium text-gray-900 dark:text-white mb-3">Additional V4.5 Innovations</h4>
			<div class="grid md:grid-cols-2 gap-3 text-sm">
				<div class="flex items-center gap-2 text-gray-600 dark:text-gray-400">
					<svg class="w-4 h-4 text-green-500 shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24">
						<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M5 13l4 4L19 7" />
					</svg>
					<span><strong>Bad Loss Penalty:</strong> Context-aware penalty for losing to weaker teams</span>
				</div>
				<div class="flex items-center gap-2 text-gray-600 dark:text-gray-400">
					<svg class="w-4 h-4 text-green-500 shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24">
						<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M5 13l4 4L19 7" />
					</svg>
					<span><strong>Bad Win Penalty:</strong> Penalty for struggling against weak teams</span>
				</div>
				<div class="flex items-center gap-2 text-gray-600 dark:text-gray-400">
					<svg class="w-4 h-4 text-green-500 shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24">
						<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M5 13l4 4L19 7" />
					</svg>
					<span><strong>Quality Win Bonus:</strong> Reward for beating significantly stronger teams</span>
				</div>
				<div class="flex items-center gap-2 text-gray-600 dark:text-gray-400">
					<svg class="w-4 h-4 text-green-500 shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24">
						<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M5 13l4 4L19 7" />
					</svg>
					<span><strong>Conference Depth:</strong> StdDev adjustment rewards deep leagues</span>
				</div>
				<div class="flex items-center gap-2 text-gray-600 dark:text-gray-400">
					<svg class="w-4 h-4 text-green-500 shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24">
						<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M5 13l4 4L19 7" />
					</svg>
					<span><strong>Bad Loss Aggregation:</strong> Conferences penalized for bad losses</span>
				</div>
				<div class="flex items-center gap-2 text-gray-600 dark:text-gray-400">
					<svg class="w-4 h-4 text-green-500 shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24">
						<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M5 13l4 4L19 7" />
					</svg>
					<span><strong>Head-to-Head Bonus:</strong> +88/+44 for Top 10/25 wins</span>
				</div>
				<div class="flex items-center gap-2 text-gray-600 dark:text-gray-400">
					<svg class="w-4 h-4 text-green-500 shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24">
						<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M5 13l4 4L19 7" />
					</svg>
					<span><strong>Quality Loss Credit:</strong> Threshold raised to 1600 Elo</span>
				</div>
				<div class="flex items-center gap-2 text-gray-600 dark:text-gray-400">
					<svg class="w-4 h-4 text-green-500 shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24">
						<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M5 13l4 4L19 7" />
					</svg>
					<span><strong>Cross-Tier Bonus:</strong> +80 per P4 win for G5 teams</span>
				</div>
				<div class="flex items-center gap-2 text-gray-600 dark:text-gray-400">
					<svg class="w-4 h-4 text-green-500 shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24">
						<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M5 13l4 4L19 7" />
					</svg>
					<span><strong>Postseason Damping:</strong> Reduced volatility for bowl games</span>
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
						Team Quality (60%) answers "How good are you?" while Resume (30%) answers "What have you actually done?" 
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
