"""Unit tests for narrative fact extraction and stub prose."""
import json
from pathlib import Path

from narrative_facts import extract_week_facts, stub_week_story, stub_why_blurbs
from shareable_blurb import BLURB_MAX_CHARS

FIXTURES = Path(__file__).parent / 'fixtures'

_BANNED_FAN_LEAKS = ('AI_MODE', 'MiniMax', 'stub narrative', 'TQ', 'CQ', 'Elo')


def _current():
    return json.loads((FIXTURES / 'sample_rankings_slim.json').read_text())


def _previous_reordered():
    """Week N-1 with Georgia #1, Oregon #2, Ohio State #3 (vs N: Oregon, OSU, Georgia)."""
    cur = _current()
    teams = {t['team_name']: dict(t) for t in cur['team_rankings']}
    return {
        'year': 2024,
        'week': 9,
        'detail': False,
        'team_rankings': [teams['Georgia'], teams['Oregon'], teams['Ohio State']],
        'conference_rankings': [],
    }


def test_extract_snapshot_only_without_previous():
    facts = extract_week_facts(_current(), None)
    assert facts['snapshot']['year'] == 2024
    assert facts['snapshot']['week'] == 10
    assert facts['snapshot']['has_wow'] is False
    assert facts['snapshot']['team_count'] == 3
    assert facts['movers'] == []
    assert facts['top_climbs'] == []
    assert facts['top_falls'] == []
    assert facts['cfp_band_changes']['entered'] == []
    assert facts['cfp_band_changes']['exited'] == []
    assert facts['top_teams'][0]['team_name'] == 'Oregon'
    assert facts['top_teams'][0]['rank'] == 1


def test_extract_wow_movers_and_cfp_band():
    facts = extract_week_facts(_current(), _previous_reordered())
    assert facts['snapshot']['has_wow'] is True

    by_name = {m['team_name']: m for m in facts['movers']}
    assert by_name['Oregon']['previous_rank'] == 2
    assert by_name['Oregon']['rank'] == 1
    assert by_name['Oregon']['delta'] == 1  # climbed 1 (prev - curr)

    assert by_name['Georgia']['previous_rank'] == 1
    assert by_name['Georgia']['rank'] == 3
    assert by_name['Georgia']['delta'] == -2

    climbs = facts['top_climbs']
    assert climbs[0]['team_name'] == 'Oregon'
    falls = facts['top_falls']
    assert falls[0]['team_name'] == 'Georgia'


def test_stub_week_story_includes_headline_and_facts():
    facts = extract_week_facts(_current(), _previous_reordered())
    story = stub_week_story(facts)
    assert story['headline']
    assert isinstance(story['paragraphs'], list)
    assert len(story['paragraphs']) >= 1
    assert story['facts'] is facts or story['facts']['snapshot']['week'] == 10
    assert 'Oregon' in story['headline'] or any('Oregon' in p for p in story['paragraphs'])
    # StoryBrand conflict headline
    assert 'jumps' in story['headline'].lower()
    assert '#1' in story['headline']
    # Body sections
    joined = ' '.join(story['paragraphs'])
    assert 'Risers:' in joined
    assert 'Taking heat:' in joined
    assert 'Who belongs higher' in joined
    # No internal AI/mode language in fan-visible copy
    for banned in _BANNED_FAN_LEAKS:
        assert banned not in story['headline']
        assert banned not in joined


def test_stub_why_blurbs_top_n_with_path_to_climb():
    result = stub_why_blurbs(_current(), top_n=2)
    blurbs = result['blurbs']
    assert set(blurbs.keys()) == {'Oregon', 'Ohio State'}
    assert 'Georgia' not in blurbs
    # Fan takes via stub_shareable_blurb
    for name, text in blurbs.items():
        assert name in text
        assert len(text) <= BLURB_MAX_CHARS
        assert '?' in text or any(
            w in text.lower() for w in ('debate', 'prove', 'fair', 'belong')
        )
        for banned in ('AI_MODE', 'MiniMax', 'TQ', 'CQ', 'our model'):
            assert banned not in text
    assert 'No. 1' in blurbs['Oregon'] or '#1' in blurbs['Oregon'] or '1' in blurbs['Oregon']
    assert 'Oregon' in blurbs['Ohio State'] or 'board' in blurbs['Ohio State'].lower()
