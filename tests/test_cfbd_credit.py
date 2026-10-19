"""The board credit and the one-key rule."""
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


def test_board_source_has_the_credit_and_one_key():
    assert credit_errors() == []
    assert forbidden_name_errors() == []
    assert CREDIT == 'Data provided by CollegeFootballData.com.'


def test_missing_credit_and_a_second_key_name_fail():
    assert credit_errors(footer='no credit', layout='<Footer />')
    assert credit_errors(footer=CREDIT, layout='<div></div>')
    assert names_in('CFBD_API_KEY' + '_B and CFBD_API_KEY' + '_SLOT')
    assert names_in('CFBD_API_KEY') == []
