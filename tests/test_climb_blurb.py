"""StoryBrand-simple path-to-climb blurbs (≤280 chars)."""
from __future__ import annotations

from shareable_blurb import (
    BLURB_MAX_CHARS,
    stub_climb_blurb,
    truncate_blurb,
)


def _context_chasing_indiana():
    return {
        'team_name': 'Ohio State',
        'rank': 4,
        'conference': 'Big Ten',
        'neighbor_ahead': 'Indiana',
        'records': {'total_wins': 12, 'total_losses': 2},
        'quality_wins': 4,
        'path_to_climb': {
            'at_top': False,
            'team_above': 'Indiana',
            'score_gap': 239.9,
            'gaps': {'tq': 27.1, 'resume': 212.7, 'cq': 0.0},
            'primary_lever': 'who they beat',
            'summary': 'To catch Indiana, Ohio State needs a stronger resume — more wins over good teams.',
        },
    }


def test_stub_climb_blurb_is_caveman_simple():
    blurb = stub_climb_blurb(_context_chasing_indiana())
    assert 40 <= len(blurb) <= BLURB_MAX_CHARS
    assert 'Indiana' in blurb
    assert 'Ohio State' in blurb
    assert 'it. Close it' in blurb
    assert 'it Close it' not in blurb
    lower = blurb.lower()
    # No math jargon (word-ish checks; avoid false positives like "below")
    for banned in ('tq contrib', 'cq Δ', 'resume Δ', 'contrib Δ', 'Δ', ' primary lever', 'elo gains'):
        assert banned not in lower
    for token in ('tq', 'cq', 'contrib', 'lever'):
        assert f' {token} ' not in f' {lower} '
    # No point-precision dumps
    assert '239' not in blurb
    assert '+27' not in blurb
    assert '+212' not in blurb
    # Debate / engagement cue
    assert '?' in blurb or any(w in lower for w in ('argue', 'debate', 'prove', 'think', 'buy'))


def test_level_on_elo_does_not_use_the_record_as_the_lever():
    blurb = stub_climb_blurb({
        'team_name': 'Soft',
        'neighbor_ahead': 'Sharp',
        'path_to_climb': {
            'at_top': False,
            'team_above': 'Sharp',
            'score_gap': 0.2,
            'gaps': {'tq': 0.16, 'resume': 400.0, 'cq': 12.0},
            'primary_lever': None,
            'summary': 'Soft matches Sharp on Elo.',
        },
    })
    lower = blurb.lower()
    assert 'level on elo' in lower
    assert 'display-only' in lower
    assert 'who they beat' not in lower
    assert 'conference' not in lower


def test_stub_climb_blurb_at_top():
    ctx = {
        'team_name': 'Indiana',
        'rank': 1,
        'neighbor_behind': 'Oregon',
        'path_to_climb': {'at_top': True, 'team_above': None},
    }
    blurb = stub_climb_blurb(ctx)
    assert len(blurb) <= BLURB_MAX_CHARS
    assert 'Indiana' in blurb
    assert '?' in blurb


def test_truncate_keeps_climb_under_limit():
    assert len(truncate_blurb('x' * 500)) <= BLURB_MAX_CHARS
