"""#149 review fix 2: priors honor the season-aware membership map, offline only."""
import json
import os
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

os.environ.setdefault('CFBD_API_KEY', 'test-key-for-unit-tests')

from conference_membership import MembershipError, load_membership  # noqa: E402
from data_processor import CFBDataProcessor  # noqa: E402
from ranking_service import ALGO_VERSION, DEFAULT_CONFIG, compute_priors, priors_cache_key  # noqa: E402
from spend_guards import CFBDOfflineError  # noqa: E402
from static_rankings import read_prior_teams, write_prior_scores  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
import precompute_rankings as pre  # noqa: E402

PUBLISHED = ROOT / 'frontend' / 'static' / 'rankings'
VERSION = load_membership().version


@pytest.fixture
def no_cache():
    with patch('ranking_service.get_cache') as mock_cache:
        cache = MagicMock()
        cache.get.return_value = None
        mock_cache.return_value = cache
        yield cache


@pytest.fixture
def no_stored_priors():
    with patch('static_rankings.read_prior_teams', return_value=None) as p:
        yield p


def _write(root, year, membership=VERSION):
    return write_prior_scores(year, {'Georgia': 1800.0}, source_sha='abc',
                              generated_at='2024-01-20T00:00:00Z', algo=ALGO_VERSION,
                              membership=membership, root=root)


# --- compute_priors --------------------------------------------------------

def test_compute_priors_reraises_membership_error(no_cache, no_stored_priors):
    dp = MagicMock()
    dp.get_games_for_season.side_effect = MembershipError('Made Up U not in 2023 map')
    with pytest.raises(MembershipError, match='Made Up U'):
        compute_priors(dp, 2024, DEFAULT_CONFIG.copy())
    no_cache.set.assert_not_called()


def test_compute_priors_fails_closed_past_coverage(no_cache, no_stored_priors):
    client = MagicMock()
    client.get_teams_with_logos.return_value = {}
    client.get_games.return_value = []
    with pytest.raises(MembershipError, match='outside conference membership coverage'):
        compute_priors(CFBDataProcessor(api_client=client), 2028, DEFAULT_CONFIG.copy())


def test_compute_priors_skips_pre_coverage_seasons_explicitly(no_cache, no_stored_priors, capsys):
    dp = MagicMock()
    dp.get_games_for_season.return_value = []
    compute_priors(dp, 2018, DEFAULT_CONFIG.copy())
    years = [c.args[0] for c in dp.get_games_for_season.call_args_list]
    assert years == [2017]
    assert 'skipping 2016, before conference membership coverage' in capsys.readouterr().out
    asked = [c.args[0] for c in no_stored_priors.call_args_list]
    assert 2016 not in asked

    dp.reset_mock()
    compute_priors(dp, 2017, DEFAULT_CONFIG.copy())
    dp.get_games_for_season.assert_not_called()


def test_compute_priors_asks_for_current_membership_version(no_cache):
    dp = MagicMock()
    dp.get_games_for_season.side_effect = AssertionError('should use stored priors')
    seen = []

    def _priors(year, algo=None, membership=None, root=None):
        seen.append(membership)
        return {'Georgia': 1800.0}

    with patch('static_rankings.read_prior_teams', side_effect=_priors):
        compute_priors(dp, 2024, DEFAULT_CONFIG.copy())
    assert seen == [VERSION, VERSION]


def test_stale_published_priors_fail_closed_offline(no_cache, tmp_path):
    """A rejected file is not reused; offline the recompute raises, never stale labels."""
    _write(tmp_path, 2023, membership='2026-11-09.1')  # older map version
    dp = MagicMock()
    dp.get_games_for_season.side_effect = CFBDOfflineError('offline')

    def _priors(year, algo=None, membership=None, root=None):
        return read_prior_teams(year, algo=algo, membership=membership, root=tmp_path)

    with patch('static_rankings.read_prior_teams', side_effect=_priors):
        with pytest.raises(CFBDOfflineError):
            compute_priors(dp, 2024, DEFAULT_CONFIG.copy())


def test_priors_cache_key_includes_membership_version():
    config = DEFAULT_CONFIG.copy()
    a = priors_cache_key(2024, config)
    other = MagicMock(version='other-map')
    with patch('ranking_service.load_membership', return_value=other):
        b = priors_cache_key(2024, config)
    assert a != b
    assert priors_cache_key(2024, config) == a


# --- stored priors files ------------------------------------------------------

def test_write_prior_scores_records_membership(tmp_path):
    path = _write(tmp_path, 2023)
    assert json.loads(path.read_text())['membership'] == VERSION
    with pytest.raises(ValueError):
        _write(tmp_path, 2022, membership='')


def test_read_prior_teams_accepts_matching_membership(tmp_path):
    _write(tmp_path, 2023)
    assert read_prior_teams(2023, algo=ALGO_VERSION, membership=VERSION, root=tmp_path) == {
        'Georgia': 1800.0}


@pytest.mark.parametrize('stored', ['2026-11-09.1', 'missing'])
def test_read_prior_teams_rejects_missing_or_other_membership(tmp_path, stored, capsys):
    path = _write(tmp_path, 2023)
    payload = json.loads(path.read_text())
    if stored == 'missing':
        payload.pop('membership')
    else:
        payload['membership'] = stored
    path.write_text(json.dumps(payload))
    assert read_prior_teams(2023, algo=ALGO_VERSION, membership=VERSION, root=tmp_path) is None
    assert 'rejected' in capsys.readouterr().out


def test_read_prior_teams_requires_membership_argument(tmp_path):
    _write(tmp_path, 2023)
    with pytest.raises(TypeError):
        read_prior_teams(2023, algo=ALGO_VERSION, root=tmp_path)


@pytest.mark.parametrize('year', [2024, 2025])
def test_committed_priors_are_rejected_until_regenerated(year):
    """The committed files predate the map (no membership field): not reused."""
    payload = json.loads((PUBLISHED / 'priors' / f'{year}.json').read_text())
    assert payload['algo'] == ALGO_VERSION and 'membership' not in payload
    assert read_prior_teams(year, algo=ALGO_VERSION, membership=VERSION, root=PUBLISHED) is None


def test_ensure_priors_refetches_stale_priors(tmp_path):
    for prior in (2023, 2022):
        _write(tmp_path, prior, membership='2026-11-09.1')
    calls = []

    class Processor:
        def get_games_for_season(self, year, through_week=None, use_week_scoped_fetch=False):
            calls.append(year)
            raise CFBDOfflineError('offline')

    with pytest.raises(CFBDOfflineError):
        pre.ensure_priors(Processor(), 2024, root=tmp_path)
    assert calls == [2023]
