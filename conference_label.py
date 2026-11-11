"""Conference-row tier label. Not a rating input.

A row takes its members' tier when they share one. Mixed membership is
labelled Mixed. Published weeks tagged every FBS independent as Power 4;
that row is Mixed when more than one team is in it.
"""

MIXED_TIER = 'Mixed'
INDEPENDENTS_CONFERENCE = 'FBS Independents'
POWER_4 = 'Power 4'


def conference_row_tier(conference, stored_type, member_types):
    """Label one conference row.

    member_types is one entry per team on that row (duplicates kept).
    """
    seen = []
    for tier in member_types or []:
        if tier and tier not in seen:
            seen.append(tier)
    if len(seen) > 1:
        return MIXED_TIER
    if len(seen) == 1:
        only = seen[0]
        if (
            conference == INDEPENDENTS_CONFERENCE
            and only == POWER_4
            and len(member_types) > 1
        ):
            return MIXED_TIER
        return only
    if conference == INDEPENDENTS_CONFERENCE and stored_type == POWER_4:
        return MIXED_TIER
    return stored_type or ''
