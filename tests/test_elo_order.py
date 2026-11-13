"""Published order is Elo. Record, momentum, and the early flag are columns."""
import inspect
import json
from pathlib import Path

from ranking_algorithm import HEAT_WEIGHT, ordering_score, soft_slate_flag
from ranking_service import publish_order
from algo_lab.runner import rank_through_week

ROOT = Path(__file__).resolve().parents[1]
BOARDS_2024 = ROOT / 'frontend' / 'static' / 'rankings' / '2024'


def _game(week, home, away, hs, as_, htype, atype, hconf, aconf):
    return {
        'year': 2024,
        'week': week,
        'home_team_name': home,
        'away_team_name': away,
        'home_score': hs,
        'away_score': as_,
        'home_conference': hconf,
        'away_conference': aconf,
        'home_conference_type': htype,
        'away_conference_type': atype,
        'notes': '',
        'season_type': 'regular',
        'neutral_site': False,
    }


def _fbs(rankings):
    keep = {'Power 4', 'Group of 5', 'FBS Independents'}
    return [
        team for team in rankings['team_rankings']
        if team.get('conference_type') in keep
    ]


def test_heat_weight_stays_zero_and_is_not_the_sort_key():
    assert HEAT_WEIGHT == 0.0
    row = {
        'team_quality_score': 1510.0,
        'momentum': 4.0,
        'record_score': 2400.0,
        'record_ahead': 3.0,
        'final_ranking_score': 100.0,
    }
    assert ordering_score(row) == 1510.0


def test_publish_order_follows_elo_when_resume_disagrees():
    # Blend would put Soft first. Elo puts Sharp first.
    teams = [
        {
            'team_name': 'Soft',
            'team_quality_score': 1400.0,
            'final_ranking_score': 1800.0,
            'record_score': 2200.0,
            'momentum': 1.5,
            'record_ahead': 2.0,
            'early_season': False,
        },
        {
            'team_name': 'Sharp',
            'team_quality_score': 1600.0,
            'final_ranking_score': 1500.0,
            'record_score': 900.0,
            'momentum': -1.0,
            'record_ahead': -0.4,
            'early_season': True,
        },
    ]
    ordered = publish_order({'team_rankings': list(teams)})['team_rankings']
    assert [team['team_name'] for team in ordered] == ['Sharp', 'Soft']
    elos = [team['team_quality_score'] for team in ordered]
    assert elos == sorted(elos, reverse=True)


def test_ranker_order_matches_elo_and_columns_stay_off_the_key():
    games = [
        _game(1, 'Pretty', 'CupA', 42, 7, 'Group of 5', 'FCS', 'Sun Belt', None),
        _game(1, 'Pretty', 'CupB', 35, 3, 'Group of 5', 'FCS', 'Sun Belt', None),
        _game(2, 'Pretty', 'CupC', 28, 10, 'Group of 5', 'FCS', 'Sun Belt', None),
        _game(1, 'Battle', 'Rival', 21, 20, 'Group of 5', 'Group of 5', 'American Athletic', 'Mid-American'),
        _game(2, 'Rival', 'Battle', 24, 17, 'Group of 5', 'Group of 5', 'Mid-American', 'American Athletic'),
        _game(3, 'Battle', 'Other', 31, 14, 'Group of 5', 'Group of 5', 'American Athletic', 'Conference USA'),
    ]
    rankings, _ranker = rank_through_week(
        games,
        through_week=3,
        config={'prior_strength': 0.0},
    )
    board = _fbs(rankings)
    names = [team['team_name'] for team in board]
    by_elo = [
        team['team_name']
        for team in sorted(board, key=lambda team: team['team_quality_score'], reverse=True)
    ]
    assert names == by_elo
    by_blend = [
        team['team_name']
        for team in sorted(board, key=lambda team: team['final_ranking_score'], reverse=True)
    ]
    assert by_blend != by_elo

    assert names[0] == 'Battle'
    assert by_blend[0] == 'Pretty'
    pretty = next(team for team in board if team['team_name'] == 'Pretty')
    assert pretty['early_season'] is False
    assert pretty['record_quality_flag'] is True
    assert pretty['record_ahead'] > 0
    assert pretty['soft_win_share'] == 1.0
    assert pretty['soft_slate_flag'] is False
    assert pretty['soft_slate_flag'] is soft_slate_flag(pretty)
    assert isinstance(pretty['momentum'], float)

    cup = next(team for team in rankings['team_rankings'] if team['team_name'] == 'CupA')
    cup_decisions = cup['records']['total_wins'] + cup['records']['total_losses']
    assert cup_decisions < 3
    assert cup['early_season'] is True
    assert cup['momentum'] is None


def test_vote_counts_never_touch_the_ordering_score():
    """A too-high / too-low tally is not an input to the published order."""
    ignored = inspect.getsource(ordering_score) + inspect.getsource(publish_order)
    assert 'too_high' not in ignored
    assert 'too_low' not in ignored

    low_elo = {
        'team_name': 'Loud',
        'team_quality_score': 1400.0,
        'too_high': 1,
        'too_low': 9000,
        'final_ranking_score': 9000.0,
        'record_score': 2400.0,
        'momentum': 8.0,
    }
    high_elo = {
        'team_name': 'Quiet',
        'team_quality_score': 1700.0,
        'too_high': 9000,
        'too_low': 1,
        'final_ranking_score': 100.0,
        'record_score': 100.0,
        'momentum': -4.0,
    }
    assert ordering_score(low_elo) == 1400.0
    assert ordering_score(high_elo) == 1700.0
    ordered = publish_order({
        'team_rankings': [dict(low_elo), dict(high_elo)],
    })['team_rankings']
    assert [team['team_name'] for team in ordered] == ['Quiet', 'Loud']
    assert [team['ordering_score'] for team in ordered] == [1700.0, 1400.0]
    assert ordered[0]['too_high'] == 9000
    assert ordered[1]['too_low'] == 9000


def test_rankings_rejects_vote_query_params(client):
    for name in ('too_high', 'too_low'):
        response = client.get(f'/rankings?year=2024&week=10&{name}=1')
        assert response.status_code == 400
        body = response.get_json()
        assert body['code'] == 'formula_params'
        assert name in body['rejected']


def _week_boards_2024():
    paths = [
        path for path in BOARDS_2024.glob('week-*.json')
        if path.name.count('.') == 1
    ]
    paths.sort(key=lambda path: int(path.stem.split('-', 1)[1]))
    assert [path.name for path in paths] == [f'week-{n}.json' for n in range(1, 16)]
    return paths


def test_committed_2024_order_stays_elo_with_momentum_on_the_row():
    """Official 2024 order is Elo. Momentum is a column and does not move places."""
    assert HEAT_WEIGHT == 0.0
    rows = 0
    nulls = 0
    numbers = 0
    momentum_would_reorder = False
    for path in _week_boards_2024():
        board = json.loads(path.read_text(encoding='utf-8'))
        assert board['year'] == 2024
        assert board['algo'] == 'v5.5'
        teams = board['team_rankings']
        names = [team['team_name'] for team in teams]
        by_elo = [
            team['team_name']
            for team in sorted(
                teams,
                key=lambda team: team['team_quality_score'],
                reverse=True,
            )
        ]
        by_order = [
            team['team_name']
            for team in sorted(teams, key=ordering_score, reverse=True)
        ]
        assert names == by_elo == by_order
        republished = publish_order({'team_rankings': [dict(team) for team in teams]})
        again = [team['team_name'] for team in republished['team_rankings']]
        assert again == names
        by_momentum = [
            team['team_name']
            for team in sorted(
                teams,
                key=lambda team: (
                    team.get('momentum') is not None,
                    float(team['momentum'])
                    if team.get('momentum') is not None else 0.0,
                ),
                reverse=True,
            )
        ]
        if by_momentum != names:
            momentum_would_reorder = True
        for team in teams:
            rows += 1
            assert team['ordering_score'] == team['team_quality_score']
            assert ordering_score(team) == team['team_quality_score']
            decisions = (
                team['records']['total_wins'] + team['records']['total_losses']
            )
            momentum = team['momentum']
            if decisions < 3:
                assert momentum is None
                nulls += 1
            else:
                assert isinstance(momentum, (int, float)) and not isinstance(momentum, bool)
                numbers += 1
    assert rows > 0
    assert nulls > 0
    assert numbers > 0
    assert momentum_would_reorder
