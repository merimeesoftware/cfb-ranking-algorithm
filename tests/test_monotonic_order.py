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


def test_published_sort_is_elo_when_the_blend_disagrees():
    """The list order itself is Elo. Reverting the sort call to the blend goes red."""
    games = [
        _game(1, 'Pretty', 'CupA', 42, 7, 'Group of 5', 'FCS'),
        _game(1, 'Pretty', 'CupB', 35, 3, 'Group of 5', 'FCS'),
        _game(2, 'Pretty', 'CupC', 28, 10, 'Group of 5', 'FCS'),
        _game(1, 'Battle', 'Rival', 21, 20, 'Group of 5', 'Group of 5'),
        _game(2, 'Rival', 'Battle', 24, 17, 'Group of 5', 'Group of 5'),
        _game(3, 'Battle', 'Other', 31, 14, 'Group of 5', 'Group of 5'),
    ]
    # Conference names on G5-G5 games need real leagues so tiers stick.
    for game, home_conf, away_conf in (
        (games[3], 'American Athletic', 'Mid-American'),
        (games[4], 'Mid-American', 'American Athletic'),
        (games[5], 'American Athletic', 'Conference USA'),
    ):
        game['home_conference'] = home_conf
        game['away_conference'] = away_conf
    for game in games[:3]:
        game['home_conference'] = 'Sun Belt'
        game['away_conference'] = None

    rankings, _ranker = rank_through_week(games, 3, config={'prior_strength': 0.0})
    keep = {'Power 4', 'Group of 5', 'FBS Independents'}
    board = [team for team in rankings['team_rankings'] if team.get('conference_type') in keep]
    elos = [team['team_quality_score'] for team in board]
    blends = [team['final_ranking_score'] for team in board]
    assert elos == sorted(elos, reverse=True)
    assert blends != sorted(blends, reverse=True)
    assert board[0]['team_name'] == 'Battle'
