import { conferenceRowTier } from './conferenceLabel.js';

type TierCarrier = { conference: string; conference_type?: string };

/** Relabel conference rows. Does not change team ratings. */
export function labelConferenceRows<T extends TierCarrier>(conferences: T[], teams: TierCarrier[]): T[] {
	const members = new Map<string, string[]>();
	for (const team of teams) {
		if (!team.conference) continue;
		const list = members.get(team.conference) || [];
		list.push(team.conference_type || '');
		members.set(team.conference, list);
	}
	return conferences.map((conf) => ({
		...conf,
		conference_type: conferenceRowTier(
			conf.conference,
			conf.conference_type || '',
			members.get(conf.conference) || []
		),
	}));
}
