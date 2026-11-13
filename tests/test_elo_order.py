"""Published order is Elo. Record, momentum, and the early flag are columns."""
from ranking_algorithm import HEAT_WEIGHT, ordering_score, soft_slate_flag
from ranking_service import publish_order
from algo_lab.runner import rank_through_week


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
