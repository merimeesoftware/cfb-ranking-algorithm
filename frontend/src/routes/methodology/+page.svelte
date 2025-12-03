<script lang="ts">
	// Methodology page
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
		</div>
	</div>

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
