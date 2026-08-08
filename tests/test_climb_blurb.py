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
