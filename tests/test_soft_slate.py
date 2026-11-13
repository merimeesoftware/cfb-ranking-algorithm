"""Display-only slate label. It does not enter the Elo order.

The 2024 week boards are the lock. A path containing 2025 is refused and
is not opened. Copy slots stay empty.
"""
import inspect
import json
import re
from pathlib import Path

import pytest

from algo_lab.runner import rank_through_week
from ranking_algorithm import (
    SOFT_SLATE_MIN_DECISIONS,
    SOFT_SLATE_MIN_SOFT_WIN_SHARE,
    SOFT_SLATE_MIN_WIN_RATE,
    ordering_score,
    soft_slate_flag,
)
from ranking_service import formula_breakdown, publish_order
from scripts.open_rankings_pr import is_sealed_path

ROOT = Path(__file__).resolve().parents[1]
RANKINGS = ROOT / 'frontend' / 'static' / 'rankings'
WEEK_FILE = re.compile(r'^week-(\d+)\.json$')
FBS = {'Power 4', 'Group of 5', 'FBS Independents'}
BANNED_PUBLIC_WORD = 'fr' + 'aud'

WEEK_6_FLAGGED = sorted(['Indiana', 'Miami', 'Ole Miss', 'Duke', 'Sam Houston'])
WEEK_15_FLAGGED = sorted([
    'Army', 'Boise State', 'Memphis', 'Ohio', 'Marshall', 'Sam Houston',
])


def _row(wins, losses, quality_wins, soft_win_share, record_ahead=0.0):
    return {
        'records': {'total_wins': wins, 'total_losses': losses},
        'quality_wins': quality_wins,
        'soft_win_share': soft_win_share,
        'record_ahead': record_ahead,
    }


def refuse_2025(path: Path) -> None:
    """Refuse before any read. 2025 stays sealed."""
    posix = path.as_posix()
    marker = 'frontend/static/rankings/'
    relative = posix[posix.index(marker):] if marker in posix else posix
    if '2025' in posix or is_sealed_path(relative):
        raise ValueError(f'refusing a path that contains 2025: {posix}')


def read_week_board(path: Path) -> dict:
    refuse_2025(path)
    if not WEEK_FILE.match(path.name):
        raise ValueError(f'not a week board: {path.name}')
    return json.loads(path.read_text(encoding='utf-8'))


def iter_2024_week_boards():
    year_dir = RANKINGS / '2024'
    paths = [path for path in sorted(year_dir.iterdir()) if WEEK_FILE.match(path.name)]
    assert paths, '2024 week boards are the lock'
    for path in paths:
        yield path, read_week_board(path)


def _fbs(payload):
    return [
        team for team in payload['team_rankings']
        if team.get('conference_type') in FBS
    ]


def _flagged(teams):
    return sorted(team['team_name'] for team in teams if soft_slate_flag(team))


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


def test_three_wins_stay_off_six_turn_on_and_a_quality_win_turns_off():
    assert soft_slate_flag(_row(3, 0, 0, 1.0, record_ahead=3.0)) is False
    six = _row(6, 0, 0, 1.0, record_ahead=-1.0)
    assert soft_slate_flag(six) is True
    assert soft_slate_flag(_row(6, 0, 1, 1.0)) is False
    # The ahead number is not a gate, including when it is negative.
    assert six['record_ahead'] < 0
    stored = dict(six)
    stored['soft_slate_flag'] = False
    assert soft_slate_flag(stored) is True


@pytest.mark.parametrize(
    ('wins', 'losses', 'quality', 'share', 'expected'),
    [
        (6, 2, 0, 0.50, True),
        (5, 1, 0, 0.50, True),
        (5, 0, 0, 1.0, False),
        (4, 2, 0, 1.0, False),
        (6, 0, 0, 0.49, False),
        (8, 0, 0, None, False),
        (6, 0, None, 1.0, False),
    ],
)
def test_soft_slate_floors(wins, losses, quality, share, expected):
    assert soft_slate_flag(_row(wins, losses, quality, share)) is expected


def test_top_level_wins_match_the_records_shape():
    assert soft_slate_flag({
        'wins': 6,
        'losses': 0,
        'quality_wins': 0,
        'soft_win_share': 0.5,
    }) is True


def test_soft_slate_does_not_change_the_sort():
    assert 'soft_slate' not in inspect.getsource(ordering_score)
    low = {
        'team_name': 'Soft',
        'team_quality_score': 1400.0,
        'soft_slate_flag': True,
        'record_ahead': 4.0,
        'final_ranking_score': 2000.0,
        **_row(8, 0, 0, 1.0, record_ahead=4.0),
    }
    high = {
        'team_name': 'Sharp',
        'team_quality_score': 1600.0,
        'soft_slate_flag': False,
        'record_ahead': -1.0,
        'final_ranking_score': 900.0,
        **_row(6, 2, 3, 0.2, record_ahead=-1.0),
    }
    assert ordering_score(low) == 1400.0
    assert ordering_score({**low, 'soft_slate_flag': False}) == ordering_score(low)
    ordered = publish_order({'team_rankings': [dict(low), dict(high)]})['team_rankings']
    assert [team['team_name'] for team in ordered] == ['Sharp', 'Soft']


def test_six_cupcake_wins_set_the_column_and_elo_still_sorts():
    games = []
    for week in range(1, 7):
        games.append(_game(
            week, 'Soft', f'Cup{week}', 35, 0,
            'Group of 5', 'FCS', 'Sun Belt', None,
        ))
        games.append(_game(
            week, 'Sharp', f'Peer{week}', 24, 17,
            'Power 4', 'Power 4', 'SEC', 'Big Ten',
        ))
    rankings, _ranker = rank_through_week(
        games,
        through_week=6,
        config={'prior_strength': 0.0},
    )
    board = _fbs(rankings)
    names = [team['team_name'] for team in board]
    by_elo = [
        team['team_name']
        for team in sorted(board, key=lambda team: team['team_quality_score'], reverse=True)
    ]
    assert names == by_elo
    soft = next(team for team in board if team['team_name'] == 'Soft')
    assert soft['records']['total_wins'] == 6
    assert soft['records']['total_losses'] == 0
    assert soft['quality_wins'] == 0
    assert soft['soft_win_share'] == 1.0
    assert soft['soft_slate_flag'] is True
    assert soft['soft_slate_flag'] is soft_slate_flag(soft)
    marked = dict(soft)
    marked['quality_wins'] = 1
    assert soft_slate_flag(marked) is False
    assert ordering_score(soft) == soft['team_quality_score']
    sharp = next(team for team in board if team['team_name'] == 'Sharp')
    assert ordering_score(sharp) > ordering_score(soft)


def test_breakdown_keeps_elo_and_names_the_end_of_week_basis():
    team = {
        'team_quality_score': 1400.0,
        'record_score': 10,
        'conference_quality_score': 20,
        'soft_slate_flag': False,
        **_row(6, 0, 0, 1.0, record_ahead=2.5),
    }
    breakdown = formula_breakdown(team)
    assert breakdown['ordering'] == 'elo'
    assert breakdown['total'] == 1400.0
    display = breakdown['display_only']
    assert display['soft_slate_flag'] is True
    assert display['record_ahead'] == 2.5
    assert display['soft_win_share'] == 1.0
    basis = display['soft_win_share_basis'].lower()
    assert 'end-of-week elo' in basis
    assert BANNED_PUBLIC_WORD not in basis


def test_reader_refuses_a_path_containing_2025(monkeypatch):
    sealed = RANKINGS / '2025' / 'week-1.json'
    priors = RANKINGS / 'priors' / '2025.json'
    opened = []
    real_read = Path.read_text

    def spy(self, *args, **kwargs):
        if '2025' in self.as_posix():
            opened.append(self.as_posix())
        return real_read(self, *args, **kwargs)

    monkeypatch.setattr(Path, 'read_text', spy)
    with pytest.raises(ValueError, match='2025'):
        read_week_board(sealed)
    with pytest.raises(ValueError, match='2025'):
        read_week_board(priors)
    assert opened == []
    assert is_sealed_path('frontend/static/rankings/2025/week-1.json') is True


def test_2024_weeks_lock_the_slate_label_and_leave_oregon_off():
    seen = []
    for path, payload in iter_2024_week_boards():
        assert path.parent.name == '2024'
        assert '2025' not in path.as_posix()
        week = int(WEEK_FILE.match(path.name).group(1))
        seen.append(week)
        for team in payload['team_rankings']:
            ahead = team.get('record_ahead')
            assert isinstance(ahead, (int, float))
            assert team['record_quality_flag'] is (ahead > 0.0)
        flagged = _flagged(_fbs(payload))
        if week == 6:
            assert flagged == WEEK_6_FLAGGED
        if week == 15:
            assert flagged == WEEK_15_FLAGGED
            oregon = next(
                team for team in payload['team_rankings']
                if team['team_name'] == 'Oregon'
            )
            assert soft_slate_flag(oregon) is False
            assert oregon['quality_wins'] > 0
            assert oregon['record_quality_flag'] is True
    assert sorted(seen) == list(range(1, 16))


def test_client_floors_match_and_copy_slots_stay_empty_and_unrendered():
    source = (ROOT / 'frontend' / 'src' / 'lib' / 'softSlate.ts').read_text(encoding='utf-8')
    brand = (ROOT / 'frontend' / 'src' / 'lib' / 'brand.ts').read_text(encoding='utf-8')

    def ts_number(text, name):
        match = re.search(rf'export const {name} = ([0-9]+(?:\.[0-9]+)?);', text)
        assert match, name
        return float(match.group(1))

    assert ts_number(source, 'SOFT_SLATE_MIN_DECISIONS') == SOFT_SLATE_MIN_DECISIONS
    assert ts_number(source, 'SOFT_SLATE_MIN_WIN_RATE') == SOFT_SLATE_MIN_WIN_RATE
    assert ts_number(source, 'SOFT_SLATE_MIN_SOFT_WIN_SHARE') == SOFT_SLATE_MIN_SOFT_WIN_SHARE
    assert 'ordering_score' not in source
    assert 'raw.soft_slate_flag' not in source.split('not read', 1)[-1]
    assert BANNED_PUBLIC_WORD not in source.lower()

    slot = re.search(r'export const SOFT_SLATE_COPY = \{([^}]+)\}', brand)
    assert slot, 'Phil still needs the copy slots'
    body = slot.group(1)
    assert "note: ''" in body
    assert "aheadLabel: ''" in body
    assert BANNED_PUBLIC_WORD not in brand.lower()

    data_files = {
        'softSlate.ts',
        'brand.ts',
        'types.ts',
        'api.ts',
        'staticRankings.ts',
        'order.ts',
    }
    offenders = []
    frontend = ROOT / 'frontend' / 'src'
    for path in frontend.rglob('*'):
        if path.suffix not in {'.svelte', '.ts'}:
            continue
        if path.name in data_files and path.suffix == '.ts':
            continue
        text = path.read_text(encoding='utf-8')
        if 'SOFT_SLATE_COPY' in text or 'soft_slate_flag' in text or 'softSlate' in text:
            offenders.append(path.relative_to(ROOT).as_posix())
    assert offenders == []
