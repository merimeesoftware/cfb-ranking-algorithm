"""A bigger win, and an extra FCS win, never lower season-end Elo.

The ×1.18 step at a 150-point live gap is off. These checks cover that path.
"""
import random
from copy import deepcopy

from algo_lab.runner import rank_through_week
from ranking_algorithm import ordering_score


def _game(week, home, away, home_score, away_score, home_type='Power 4', away_type='Power 4',
          home_conf='SEC', away_conf='SEC'):
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


def _end(games, name, priors=None, strength=0.0):
    week = max(int(game['week']) for game in games)
    rankings, _ranker = rank_through_week(
        games,
        week,
        config={'prior_strength': strength},
        priors=priors or {},
    )
    teams = rankings['team_rankings']
    scores = [ordering_score(team) for team in teams]
    assert scores == sorted(scores, reverse=True)
    return ordering_score(next(team for team in teams if team['team_name'] == name))


def test_archie_bigger_margin_then_upset_does_not_fall():
    """Alpha 1500 beats Beta 1100 by 7 vs 14, then wins at Gamma 1658."""
    priors = {'Alpha': 1500.0, 'Beta': 1100.0, 'Gamma': 1658.0}

    def games(margin):
        return [
            _game(1, 'Alpha', 'Beta', 10 + margin, 10),
            _game(2, 'Gamma', 'Alpha', 10, 40),
        ]

    small = _end(games(7), 'Alpha', priors, strength=1.0)
    big = _end(games(14), 'Alpha', priors, strength=1.0)
    assert big + 1e-9 >= small


def test_archie_extra_fcs_win_then_upset_does_not_fall():
    """Extra 35-0 FCS win before Alpha wins at Gamma 1680.

    Delta starts at 1500 and the first game is 24-21. Restoring the
    1.18 upset bonus makes the extra win lower Alpha.
    """
    priors = {'Alpha': 1500.0, 'Delta': 1500.0, 'Gamma': 1680.0}
    base = [
        _game(1, 'Alpha', 'Delta', 24, 21),
        _game(3, 'Gamma', 'Alpha', 10, 30),
    ]
    extra = list(base)
    extra.insert(1, _game(2, 'Alpha', 'Cup', 35, 0, 'Power 4', 'FCS', 'SEC', None))
    without = _end(base, 'Alpha', priors, strength=1.0)
    with_win = _end(extra, 'Alpha', priors, strength=1.0)
    assert with_win + 1e-9 >= without


def test_clamp_at_1850_never_goes_lower():
    priors = {'Alpha': 1850.0, 'Beta': 1500.0}
    close = [_game(1, 'Alpha', 'Beta', 21, 20)]
    blowout = [_game(1, 'Alpha', 'Beta', 60, 20)]
    small = _end(close, 'Alpha', priors, strength=1.0)
    big = _end(blowout, 'Alpha', priors, strength=1.0)
    assert small == 1850.0
    assert big == 1850.0


def test_seeded_schedules_stay_monotone_at_season_end():
    rng = random.Random(20261111)
    types = ('Power 4', 'Group of 5', 'FCS')
    for _ in range(220):
        names = ['Alpha', 'Beta', 'Gamma', 'Delta']
        kind = {name: rng.choice(types) for name in names}
        kind['Alpha'] = rng.choice(('Power 4', 'Group of 5'))
        priors = {name: 1400.0 + rng.uniform(-250.0, 250.0) for name in names}
        priors['Gamma'] = priors['Alpha'] + rng.uniform(160.0, 280.0)
        games = []
        week = 1
        # The margin we vary, then a game against a higher-rated team.
        base_margin = rng.randint(1, 14)
        games.append(_game(week, 'Alpha', 'Beta', 14 + base_margin, 14, kind['Alpha'], kind['Beta']))
        week += 1
        for _pair in range(3):
            home, away = rng.sample(names, 2)
            margin = rng.randint(1, 24)
            games.append(_game(week, home, away, 10 + margin, 10, kind[home], kind[away]))
            week += 1
        games.append(_game(week, 'Gamma', 'Alpha', 10, 10 + rng.randint(3, 21), kind['Gamma'], kind['Alpha']))
        wider = deepcopy(games)
        wider[0]['home_score'] = games[0]['home_score'] + rng.randint(1, 20)
        assert _end(wider, 'Alpha', priors, 1.0) + 1e-6 >= _end(games, 'Alpha', priors, 1.0)
        extra = deepcopy(games)
        extra.insert(1, _game(2, 'Alpha', f'Cup{week}', 35, 0, kind['Alpha'], 'FCS', 'SEC', None))
        assert _end(extra, 'Alpha', priors, 1.0) + 1e-6 >= _end(games, 'Alpha', priors, 1.0)


def test_published_sort_is_elo_when_the_blend_disagrees():
    """The list order itself is Elo. Reverting the sort call to the blend goes red."""
    games = [
        _game(1, 'Pretty', 'CupA', 42, 7, 'Group of 5', 'FCS', 'Sun Belt', None),
        _game(1, 'Pretty', 'CupB', 35, 3, 'Group of 5', 'FCS', 'Sun Belt', None),
        _game(2, 'Pretty', 'CupC', 28, 10, 'Group of 5', 'FCS', 'Sun Belt', None),
        _game(1, 'Battle', 'Rival', 21, 20, 'Group of 5', 'Group of 5', 'American Athletic', 'Mid-American'),
        _game(2, 'Rival', 'Battle', 24, 17, 'Group of 5', 'Group of 5', 'Mid-American', 'American Athletic'),
        _game(3, 'Battle', 'Other', 31, 14, 'Group of 5', 'Group of 5', 'American Athletic', 'Conference USA'),
    ]
    rankings, _ranker = rank_through_week(games, 3, config={'prior_strength': 0.0})
    keep = {'Power 4', 'Group of 5', 'FBS Independents'}
    board = [team for team in rankings['team_rankings'] if team.get('conference_type') in keep]
    elos = [ordering_score(team) for team in board]
    blends = [team['final_ranking_score'] for team in board]
    assert elos == sorted(elos, reverse=True)
    assert blends != sorted(blends, reverse=True)
    assert board[0]['team_name'] == 'Battle'
