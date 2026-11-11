/**
 * Conference-row tier label. Keep in step with conference_label.py.
 * This does not change a team's rating.
 */

export const MIXED_TIER = 'Mixed';
export const INDEPENDENTS_CONFERENCE = 'FBS Independents';
const POWER_4 = 'Power 4';

/**
 * @param {string} conference
 * @param {string} storedType
 * @param {string[]} memberTypes one entry per team
 * @returns {string}
 */
export function conferenceRowTier(conference, storedType, memberTypes) {
	/** @type {string[]} */
	const seen = [];
	for (const tier of memberTypes || []) {
		if (tier && !seen.includes(tier)) seen.push(tier);
	}
	if (seen.length > 1) return MIXED_TIER;
	if (seen.length === 1) {
		const only = seen[0];
		if (conference === INDEPENDENTS_CONFERENCE && only === POWER_4 && memberTypes.length > 1) {
			return MIXED_TIER;
		}
		return only;
	}
	if (conference === INDEPENDENTS_CONFERENCE && storedType === POWER_4) return MIXED_TIER;
	return storedType || '';
}

/**
 * @param {string} type
 * @returns {string}
 */
export function tierBadgeClass(type) {
	if (type === 'Power 4') return 'badge-power4';
	if (type === 'Group of 5') return 'badge-g5';
	if (type === MIXED_TIER) return 'badge-mixed';
	return 'badge-ind';
}
