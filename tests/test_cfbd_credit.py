"""The board credit and the one-key rule."""
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))

from check_cfbd_credit import (  # noqa: E402
    CREDIT,
    credit_errors,
    forbidden_name_errors,
    names_in,
)

CHECK = ROOT / 'scripts' / 'check_cfbd_credit.py'


def test_board_source_has_the_credit_and_one_key():
    assert credit_errors() == []
    assert forbidden_name_errors() == []
    assert CREDIT == 'Data provided by CollegeFootballData.com.'


def test_missing_credit_and_a_second_key_name_fail():
    assert credit_errors(footer='no credit', layout='<Footer />')
    assert credit_errors(footer=CREDIT, layout='<div></div>')
    assert names_in('CFBD_API_KEY' + '_B and CFBD_API_KEY' + '_SLOT')
    assert names_in('CFBD_API_KEY') == []


def test_built_check_fails_when_html_and_bundle_omit_the_credit(tmp_path):
    week = tmp_path / '2099' / 'week'
    week.mkdir(parents=True)
    (week / '10.html').write_text(
        '<html><body><p>Rankings stay free.</p></body></html>',
        encoding='utf-8',
    )
    bundle = tmp_path / '_app'
    bundle.mkdir()
    (bundle / 'layout.js').write_text('var footer = "rankings stay free";', encoding='utf-8')
    proc = subprocess.run(
        [sys.executable, str(CHECK), '--built', '--build', str(tmp_path)],
        capture_output=True,
        text=True,
        check=False,
    )
    assert proc.returncode != 0
    assert 'data-cfbd-credit' in proc.stderr
    assert 'client bundle' in proc.stderr
