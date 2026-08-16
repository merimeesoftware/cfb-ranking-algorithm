/**
 * Server/build-time helpers for loading precomputed rankings from static/.
 * Import only from +page.server.ts (Node fs).
 */
import { readFileSync, existsSync } from 'node:fs';
import { join } from 'node:path';
import type { Conference, Team } from '$lib/types';

const STATIC_ROOT = join(process.cwd(), 'static', 'rankings');

export type Manifest = { years: Record<string, number[]> };

function parseWinPct(value: unknown): number {
	if (typeof value === 'number') return value;
	if (typeof value === 'string' && value.includes('-')) {
		const [wins, losses] = value.split('-').map(Number);
		const total = wins + losses;
		return total > 0 ? wins / total : 0;
	}
	return 0;
}

function mapTeam(t: Record<string, unknown>): Team {
	const records = (t.records || {}) as Record<string, number>;
	return {
		team_name: (t.team_name || t.team || '') as string,
		conference: (t.conference || '') as string,
		conference_type: (t.conference_type || '') as string,
		final_ranking_score: (t.final_ranking_score || t.score || 0) as number,
		team_quality_score: (t.team_quality_score || 0) as number,
		record_score: (t.record_score || 0) as number,
		conference_quality_score: (t.conference_quality_score || 0) as number,
		sos: (t.sos ?? null) as number | null,
		sov: (t.sov ?? null) as number | null,
		sos_rank: t.sos_rank as number | undefined,
		sov_rank: t.sov_rank as number | undefined,
		logo: (t.logo ?? null) as string | null,
		logo_dark: (t.logo_dark ?? null) as string | null,
		color: (t.color ?? null) as string | null,
		alt_color: (t.alt_color ?? null) as string | null,
		records: {
			total_wins: records.total_wins ?? 0,
			total_losses: records.total_losses ?? 0,
			conf_wins: records.conf_wins ?? 0,
			conf_losses: records.conf_losses ?? 0,
			power_wins: records.power_wins ?? 0,
			power_losses: records.power_losses ?? 0,
			group_five_wins: records.group_five_wins ?? 0,
			group_five_losses: records.group_five_losses ?? 0,
		},
		quality_wins: (t.quality_wins ?? 0) as number,
		quality_losses: (t.quality_losses ?? 0) as number,
		bad_losses: (t.bad_losses ?? 0) as number,
		bad_wins: (t.bad_wins ?? 0) as number,
		top_10_wins: (t.top_10_wins ?? 0) as number,
		top_25_wins: (t.top_25_wins ?? 0) as number,
		cross_tier_wins: (t.cross_tier_wins ?? 0) as number,
	};
}

function mapConference(c: Record<string, unknown>): Conference {
	return {
		conference: (c.conference_name || c.conference || '') as string,
		conference_type: (c.conference_type || '') as string,
		avg_ranking: (c.average_team_quality || c.avg_ranking || 0) as number,
		team_count: (c.number_of_teams || c.team_count || 0) as number,
		ranked_teams: (c.ranked_teams ?? 0) as number,
		power_win_pct: parseWinPct(c.record_vs_p4 || c.power_win_pct),
		g5_win_pct: parseWinPct(c.record_vs_g5 || c.g5_win_pct),
		fcs_wins: c.fcs_wins as number | undefined,
		fcs_losses: c.fcs_losses as number | undefined,
	};
}

export function readManifest(): Manifest {
	const path = join(STATIC_ROOT, 'manifest.json');
	if (!existsSync(path)) return { years: {} };
	return JSON.parse(readFileSync(path, 'utf-8')) as Manifest;
}

export function listPublishedWeeks(): Array<{ year: number; week: number }> {
	const manifest = readManifest();
	const out: Array<{ year: number; week: number }> = [];
	for (const [yearStr, weeks] of Object.entries(manifest.years || {})) {
		const year = Number(yearStr);
		for (const week of weeks) {
			out.push({ year, week });
		}
	}
	return out.sort((a, b) => a.year - b.year || a.week - b.week);
}

export function latestPublishedWeek(): { year: number; week: number } | null {
	const weeks = listPublishedWeeks();
	return weeks.length ? weeks[weeks.length - 1] : null;
}

export function loadWeekRankings(
	year: number,
	week: number
): { teams: Team[]; conferences: Conference[]; year: number; week: number } | null {
	const path = join(STATIC_ROOT, String(year), `week-${week}.json`);
	if (!existsSync(path)) return null;
	const data = JSON.parse(readFileSync(path, 'utf-8')) as Record<string, unknown>;
	const teams = ((data.team_rankings || data.teams || []) as Record<string, unknown>[]).map(
		mapTeam
	);
	const conferences = (
		(data.conference_rankings || data.conferences || []) as Record<string, unknown>[]
	).map(mapConference);
	return {
		teams,
		conferences,
		year: (data.year as number) || year,
		week: (data.week as number) || week,
	};
}

export function loadPrevRanks(year: number, week: number): Map<string, number> {
	const map = new Map<string, number>();
	if (week <= 1) return map;
	const prev = loadWeekRankings(year, week - 1);
	if (!prev) return map;
	prev.teams.forEach((t, i) => map.set(t.team_name, i + 1));
	return map;
}

export function loadWeekStory(
	year: number,
	week: number
): { headline?: string; paragraphs?: string[] } | null {
	const path = join(STATIC_ROOT, String(year), `week-${week}.story.json`);
	if (!existsSync(path)) return null;
	return JSON.parse(readFileSync(path, 'utf-8')) as {
		headline?: string;
		paragraphs?: string[];
	};
}
