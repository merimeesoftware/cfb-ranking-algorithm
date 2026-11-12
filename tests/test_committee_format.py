"""Hand-entered committee files (#174). No network, no 2025 board, no public table."""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / 'scripts'))

import check_board_stamps as stamps
import check_committee_format as committee_check
from committee_ingest import (
    ATTRIBUTION,
    SOURCE_OF_RECORD,
    CommitteeFormatError,
    attribution_line,
    checked_backfill,
    committee_errors,
    dumps_committee,
    hand_entered_rows,
    path_is_sealed,
    write_committee_file,
)
from public_board import ROUTE_ALLOWED
from static_rankings import rebuild_rankings_manifest

VALID = ROOT / 'tests' / 'fixtures' / 'committee' / 'valid' / '2024.json'
CFBD = ROOT / 'tests' / 'fixtures' / 'committee' / 'cfbd-backfill.json'
SEALED = ROOT / 'tests' / 'fixtures' / 'committee' / 'invalid' / '2025.json'
WEEK_NAME = ROOT / 'tests' / 'fixtures' / 'committee' / 'invalid' / 'week-10.json'
CI = ROOT / '.github' / 'workflows' / 'ci.yml'
DOC = ROOT / 'docs' / 'committee-source.md'
LEGEND = ROOT / 'frontend' / 'src' / 'lib' / 'components' / 'RankingsTable.svelte'

CONDITIONS = """1. The source of record is hand entry from the official weekly CFP release. Store only rank, team name, optional record and release date. No scraping, no release text or images, no raw CFBD JSON. The plan currently says CFBD GET /rankings; change it. CFBD is allowed only for test fixtures or a backfill, checked against the official list, and the published table is still cited to the CFP.
2. Plain-text CFP references only. No CFP or school logos, no official styling, no 'official' or 'endorsed' wording. Rename our own 'CFP Playoff (1-12)' legend before the committee column ships, and give Phil a copy slot for the new name.
3. Non-commercial for now.
Attribution line, exact: 'CFP selection committee ranking, released [DATE]. Source: collegefootballplayoff.com. Not affiliated with or endorsed by the College Football Playoff.'"""

HAND = [
    {
        'release_date': '2024-11-12',
        'rank': 1,
        'team_name': 'Example State',
        'record': '9-0',
    },
    {
        'release_date': '2024-11-12',
        'rank': 2,
        'team_name': 'Sample Tech',
        'record': '8-1',
    },
]


def _load(path):
    return json.loads(path.read_text(encoding='utf-8'))


def test_legal_conditions_are_verbatim():
    assert CONDITIONS in DOC.read_text(encoding='utf-8')
    assert ATTRIBUTION == (
        'CFP selection committee ranking, released [DATE]. '
        'Source: collegefootballplayoff.com. '
        'Not affiliated with or endorsed by the College Football Playoff.'
    )
    assert attribution_line('2024-11-12') == ATTRIBUTION.replace('[DATE]', '2024-11-12')


def test_valid_fixture_is_hand_entered_and_canonical():
    raw = VALID.read_text(encoding='utf-8')
    payload = json.loads(raw)
    assert committee_errors(payload, filename='2024.json') == []
    assert dumps_committee(payload) == raw
    assert 'algo' not in raw
    assert 'ALGO_VERSION' not in raw
    assert 'v5.5' not in raw
    assert SOURCE_OF_RECORD == 'hand-entry'
    assert 'hand-entry' not in raw
    assert 'poll' not in raw


def test_algo_stamp_is_refused():
    payload = _load(VALID)
    payload[0]['algo'] = 'v5.5'
    errors = committee_errors(payload, filename='2024.json')
    assert any('ALGO_VERSION' in error for error in errors)
    payload[0].pop('algo')
    payload[0]['ALGO_VERSION'] = 'v5.5'
    errors = committee_errors(payload, filename='2024.json')
    assert any('ALGO_VERSION' in error for error in errors)


def test_stamp_value_and_live_stamp_are_refused():
    payload = _load(VALID)
    payload[0]['team_name'] = 'v5.5'
    assert any('v5.5' in error for error in committee_errors(payload, filename='2024.json'))
    payload[0]['team_name'] = 'v9.9'
    errors = committee_errors(payload, filename='2024.json', forbidden_stamps=('v9.9',))
    assert any('v9.9' in error for error in errors)


def test_raw_cfbd_json_is_not_a_committee_file():
    errors = committee_errors(_load(CFBD), filename='2024.json')
    assert errors
    assert any('CFBD' in error or 'not stored' in error for error in errors)
    text = CFBD.read_text(encoding='utf-8')
    assert 'AP Top 25' in text
    assert 'Coaches Poll' in text


def test_backfill_keeps_hand_entry_when_names_match():
    body = _load(CFBD)
    stored = checked_backfill(HAND, body)
    assert stored[0]['record'] == '9-0'
    assert [row['team_name'] for row in stored] == ['Example State', 'Sample Tech']
    dumped = dumps_committee(stored)
    for banned in ('AP Top 25', 'Coaches Poll', 'firstPlaceVotes', 'polls', 'algo', 'week'):
        assert banned not in dumped
    body[0]['week'] = 99
    assert checked_backfill(HAND, body) == stored


def test_backfill_refuses_a_mismatch_and_does_not_return_rows():
    wrong = [dict(row) for row in HAND]
    wrong[1] = dict(wrong[1], team_name='Fixture A&M')
    try:
        checked_backfill(wrong, _load(CFBD))
    except CommitteeFormatError as exc:
        assert any('does not match' in error for error in exc.errors)
    else:
        raise AssertionError('mismatch must not return rows')


def test_backfill_refuses_2025_without_returning_rows():
    body = [{
        'season': 2025,
        'seasonType': 'regular',
        'week': 12,
        'polls': [{
            'poll': 'Playoff Committee Rankings',
            'ranks': [{'rank': 1, 'school': 'Sealed Example'}],
        }],
    }]
    try:
        checked_backfill(HAND, body)
    except CommitteeFormatError as exc:
        assert any('2025' in error for error in exc.errors)
    else:
        raise AssertionError('2025 must be refused')


def test_sealed_file_and_week_name_are_refused():
    sealed_errors = committee_check.file_errors(SEALED)
    assert any('2025 is the sealed holdout.' in error for error in sealed_errors)
    week_errors = committee_check.file_errors(WEEK_NAME)
    assert any('week-N.json' in error for error in week_errors)
    assert committee_check.main([str(SEALED.parent)]) == 1


def test_extra_fields_records_and_duplicates():
    row = dict(HAND[0])
    prose = dict(row, record='eight and oh')
    assert any('record' in error for error in committee_errors([prose]))
    duplicate = [dict(HAND[0]), dict(HAND[0])]
    assert any('repeats rank' in error for error in committee_errors(duplicate))
    bare = {'release_date': '2024-11-12', 'rank': 1, 'team_name': 'Example State'}
    assert committee_errors([bare]) == []
    assert 'record' not in hand_entered_rows([bare])[0]


def test_writer_does_not_stamp_or_touch_manifest(tmp_path):
    path = write_committee_file(tmp_path / 'committee', _load(VALID), year=2024)
    assert path.name == '2024.json'
    text = path.read_text(encoding='utf-8')
    assert '"algo"' not in text
    assert 'ALGO_VERSION' not in text
    try:
        write_committee_file(tmp_path / '2025', _load(VALID), year=2025)
    except CommitteeFormatError as exc:
        assert any('2025' in error for error in exc.errors)
    else:
        raise AssertionError('2025 must not be written')


def test_sealed_path_is_refused_when_year_is_not_2025(tmp_path):
    sealed = tmp_path / '2025' / 'committee'
    try:
        write_committee_file(sealed, _load(VALID), year=2024)
    except CommitteeFormatError as exc:
        assert any('2025 is the sealed holdout.' in error for error in exc.errors)
    else:
        raise AssertionError('a 2025 directory must be refused')
    assert not sealed.exists()
    assert not (tmp_path / '2025').exists()
    nested = tmp_path / 'rankings' / '2025' / 'committee'
    assert path_is_sealed(nested / '2024.json')
    flagged = committee_check.file_errors(nested / '2024.json')
    assert any('2025 is the sealed holdout.' in error for error in flagged)
    assert not nested.exists()


def test_manifest_and_board_stamp_ignore_committee_files(tmp_path):
    week = tmp_path / '2024'
    week.mkdir()
    (week / 'week-1.json').write_text('{"algo": "v5.5"}', encoding='utf-8')
    committee = tmp_path / 'committee'
    committee.mkdir()
    (committee / '2024.json').write_text(VALID.read_text(encoding='utf-8'), encoding='utf-8')
    assert rebuild_rankings_manifest(tmp_path) == {'years': {'2024': [1]}}
    assert 'committee' not in (tmp_path / 'manifest.json').read_text(encoding='utf-8')
    assert stamps.board_stamp_errors(tmp_path) == []
    assert committee_check.published_errors(tmp_path) == []


def test_checker_accepts_repo_and_ci_runs_it():
    assert committee_check.main([]) == 0
    assert 'scripts/check_committee_format.py' in CI.read_text(encoding='utf-8')


def test_no_public_committee_surface_and_legend_stays():
    assert 'committee' not in ROUTE_ALLOWED
    surfaces = [
        ROOT / 'app.py',
        ROOT / 'public_board.py',
        ROOT / 'worker' / 'src' / 'index.ts',
        LEGEND,
    ]
    for path in surfaces:
        text = path.read_text(encoding='utf-8')
        assert '/rankings/committee' not in text
        assert "route('/committee" not in text
    svelte = LEGEND.read_text(encoding='utf-8')
    assert 'CFP Playoff (1-12)' in svelte
    doc = DOC.read_text(encoding='utf-8')
    row = next(line for line in doc.splitlines() if line.startswith('| Gold 1-12 legend |'))
    cells = [cell.strip() for cell in row.strip('|').split('|')]
    assert cells[0] == 'Gold 1-12 legend'
    assert cells[1] == 'CFP Playoff (1-12)'
    assert cells[2] == ''
    copy_table = (ROOT / 'docs' / 'design' / 'phil-copy-table.md').read_text(encoding='utf-8')
    assert '| Gold 1-12 legend | CFP Playoff (1-12) |' in copy_table


def test_planted_manifest_and_algo_file_fail(tmp_path):
    (tmp_path / 'manifest.json').write_text('{"committee": true}\n', encoding='utf-8')
    committee = tmp_path / 'committee'
    committee.mkdir()
    payload = _load(VALID)
    payload[0]['algo'] = 'v5.5'
    (committee / '2024.json').write_text(json.dumps(payload), encoding='utf-8')
    errors = committee_check.published_errors(tmp_path)
    assert any('manifest' in error for error in errors)
    assert any('ALGO_VERSION' in error for error in errors)
    assert committee_check.main([str(tmp_path)]) == 1


def test_module_does_not_call_cfbd_or_open_the_holdout():
    text = (ROOT / 'committee_ingest.py').read_text(encoding='utf-8')
    assert 'collegefootballdata' not in text
    assert 'urllib' not in text
    assert 'requests' not in text
    assert 'priors/2025' not in text
    assert 'compare_top4' not in text
    try:
        attribution_line('2025-11-04')
    except CommitteeFormatError as exc:
        assert any('2025' in error for error in exc.errors)
    else:
        raise AssertionError('2025 attribution must be refused')
