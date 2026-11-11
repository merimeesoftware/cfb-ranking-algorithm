"""A bigger win, and an extra FCS win, never lower the ordering score.

The résumé can still fall. The published order is Elo, so it does not.
"""
from algo_lab.runner import rank_through_week
from ranking_algorithm import ordering_score


def _game(week, home, away, home_score, away_score, home_type='Power 4', away_type='Power 4'):
    home_conf = 'SEC' if home_type == 'Power 4' else None
    away_conf = 'SEC' if away_type == 'Power 4' else None
    return {
        'year': 2024,
        'week': week,
        'home_team_name': home,
        'away_team_name': away,
        'home_score': home_score,
        'away_score': away_score,
        'home_conference': home_conf,
        'away_conference': away_conf,
        'home_conference_type': home_type,
        'away_conference_type': away_type,
        'notes': '',
        'season_type': 'regular',
        'neutral_site': False,
    }


def _team(games, name, week):
    rankings, _ranker = rank_through_week(games, week, config={'prior_strength': 0.0})
    return next(team for team in rankings['team_rankings'] if team['team_name'] == name)


def test_bigger_margin_never_lowers_ordering_score():
    # Beta is parked just above the schedule baseline. A larger margin pushes
    # Beta under that line, and the résumé falls. Elo does not.
    close = [
        _game(1, 'Keeper', 'Beta', 17, 14),
        _game(2, 'Alpha', 'Beta', 21, 14),
    ]
    blowout = [
        _game(1, 'Keeper', 'Beta', 17, 14),
        _game(2, 'Alpha', 'Beta', 28, 14),
    ]
    small = _team(close, 'Alpha', 2)
    big = _team(blowout, 'Alpha', 2)
    assert big['final_ranking_score'] < small['final_ranking_score']
    assert ordering_score(big) == big['team_quality_score']
    assert ordering_score(big) >= ordering_score(small)


def test_extra_fcs_win_never_lowers_ordering_score():
    slate = []
    for week, opponent in enumerate(('Bravo', 'Charlie', 'Delta', 'Echo'), start=1):
        slate.append(_game(week, 'Alpha', opponent, 24, 17))
        slate.append(_game(week, opponent, f'Filler {opponent}', 28, 10))
    extra = list(slate)
    extra.append(_game(4, 'Alpha', 'Cupcake', 35, 0, 'Power 4', 'FCS'))
    before = _team(slate, 'Alpha', 4)
    after = _team(extra, 'Alpha', 4)
    assert after['final_ranking_score'] < before['final_ranking_score']
    assert ordering_score(after) == after['team_quality_score']
    assert ordering_score(after) >= ordering_score(before)
