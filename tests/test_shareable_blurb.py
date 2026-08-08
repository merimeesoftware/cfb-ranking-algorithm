"""Shareable team blurbs (≤280 chars) with season-aware cache periods."""
from __future__ import annotations

from datetime import date

from shareable_blurb import (
    BLURB_MAX_CHARS,
    blurb_cache_period,
    is_in_season,
    stub_shareable_blurb,
    truncate_blurb,
)


def test_blurb_max_chars_is_x_limit():
    assert BLURB_MAX_CHARS == 280


def test_in_season_daily_vs_offseason_monthly():
    assert is_in_season(date(2025, 9, 15)) is True
    assert blurb_cache_period(date(2025, 9, 15)) == '2025-09-15'
    assert is_in_season(date(2026, 3, 1)) is False
    assert blurb_cache_period(date(2026, 3, 1)) == '2026-03'
    # Pre-tip-off August is still offseason for cache purposes
    assert is_in_season(date(2026, 8, 10)) is False
    assert blurb_cache_period(date(2026, 8, 10)) == '2026-08'


def test_stub_shareable_blurb_fits_and_has_why_plus_hook():
    context = {
        'team_name': 'Indiana',
        'rank': 1,
        'conference': 'Big Ten',
        'final_ranking_score': 2159.2,
        'team_quality_score': 2000,
        'record_score': 2100,
        'conference_quality_score': 1600,
        'records': {'total_wins': 16, 'total_losses': 0},
        'quality_wins': 4,
        'path_to_climb': {'at_top': True, 'summary': 'Indiana is currently #1.'},
        'neighbor_behind': 'Oregon',
    }
    blurb = stub_shareable_blurb(context)
    assert 40 <= len(blurb) <= BLURB_MAX_CHARS
    assert 'Indiana' in blurb
    assert '#' in blurb or 'No.' in blurb or '1' in blurb
    # Debate/hook cue
    assert any(token in blurb.lower() for token in ('?', 'debate', 'argue', 'prove', 'still', 'case'))


def test_truncate_blurb_respects_limit():
    long = 'x' * 400
    out = truncate_blurb(long)
    assert len(out) <= BLURB_MAX_CHARS


def test_truncate_prefers_complete_sentence_no_ellipsis():
    # Model overshoots; keep last full sentence inside the cap — no mid-thought "…"
    long = (
        'Indiana sits at No. 1 with a 16-0 record, including an unbeaten 11-0 Big Ten mark, '
        '13 power-conference wins, and seven quality victories over elite opponents like '
        'Alabama, Oregon, and Miami. Zero losses, zero bad losses, and a top-tier team '
        'quality score carry the Hoosiers to the top of the board. Who can knock them off?'
    )
    assert len(long) > BLURB_MAX_CHARS
    out = truncate_blurb(long)
    assert len(out) <= BLURB_MAX_CHARS
    assert not out.endswith('…')
    assert out.endswith('.') or out.endswith('?') or out.endswith('!')


def test_extract_blurb_rejects_raw_api_dump():
    from shareable_blurb import extract_blurb_text

    assert extract_blurb_text("{'id': 'x', 'content': []}") == ''
    assert extract_blurb_text('LLM explanation unavailable: empty text content') == ''
    assert extract_blurb_text('"Clean take on Indiana at No. 1. Debate?"') == (
        'Clean take on Indiana at No. 1. Debate?'
    )


def test_extract_blurb_rejects_over_limit_without_cutting():
    """Live path must not silently chop — over-length returns empty for retry/stub."""
    from shareable_blurb import extract_blurb_text

    long = (
        'Indiana sits at No. 1 with a 16-0 record, including an unbeaten 11-0 Big Ten mark, '
        '13 power-conference wins, and seven quality victories over elite opponents like '
        'Alabama, Oregon, and Miami. Zero losses, zero bad losses, and a top-tier team '
        'quality score carry the Hoosiers to the top of the board. Who can knock them off?'
    )
    assert len(long) > BLURB_MAX_CHARS
    assert extract_blurb_text(long) == ''


def test_accept_only_fits_hard_cap():
    from shareable_blurb import accept_blurb

    ok = 'Indiana is No. 1 at 16-0. Can Oregon catch them?'
    assert accept_blurb(ok) == ok
    assert accept_blurb('x' * 281) == ''
    assert accept_blurb('') == ''
