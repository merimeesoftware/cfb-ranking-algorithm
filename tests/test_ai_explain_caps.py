"""Allowlisted explain prompts, per-provider cache, and closed budgets."""
import json
import sys
from pathlib import Path
from unittest.mock import patch

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))

from check_ai_providers import (  # noqa: E402
    canon_scan_exclusions,
    closed_budget_errors,
    contains_retired_name,
    evaluate,
    filter_retired_name_hits,
    retired_name_hits,
)

FIXTURES = Path(__file__).parent / 'fixtures' / 'caps'


def _load(name: str) -> dict:
    return json.loads((FIXTURES / name).read_text(encoding='utf-8'))


def _rankings() -> dict:
    return json.loads(
        (Path(__file__).parent / 'fixtures' / 'sample_rankings_slim.json').read_text()
    )


class _Response:
    def __init__(self, payload: dict):
        self._payload = json.dumps(payload).encode()

    def read(self):
        return self._payload

    def __enter__(self):
        return self

    def __exit__(self, *_args):
        return False


def test_unknown_question_id_is_400(client, monkeypatch):
    fixture = _load('question_id_rejected.json')
    monkeypatch.setenv('AI_MODE', 'stub')
    rejected = client.post('/agent/explain', json={
        'team_name': 'Oregon',
        'year': 2024,
        'week': 10,
        'question_id': fixture['question_id'],
    })
    assert rejected.status_code == 400
    assert rejected.get_json()['code'] == 'question_id'
    free_text = client.post('/agent/explain', json={
        'team_name': 'Oregon',
        'year': 2024,
        'week': 10,
        'question_id': 'why_here',
        'question': fixture['question'],
    })
    assert free_text.status_code == 400


def test_planted_open_budgets_fail_and_production_stays_closed():
    planted = _load('xai_budget_open.json')
    assert closed_budget_errors(planted['limit'])
    assert evaluate() == []


def test_xai_explain_is_refused_when_the_cap_is_raised(client, monkeypatch):
    fixture = _load('xai_repeat_explain.json')
    monkeypatch.setenv('AI_MODE', 'live')
    monkeypatch.setenv('XAI_ENABLED', '1')
    monkeypatch.setenv('XAI_MAX_CALLS', '5')
    monkeypatch.setenv('AI_XAI_HOST', 'ai.xai')
    monkeypatch.delenv('AI_KILL', raising=False)
    monkeypatch.delenv('XAI_KILL', raising=False)
    monkeypatch.delenv('SPEND_GATE_HOST', raising=False)
    from agent_service import explain_cache_logical
    from cache import get_cache
    from shareable_blurb import blurb_cache_period

    cache = get_cache()
    logical = explain_cache_logical(
        'xai',
        fixture['year'],
        fixture['week'],
        fixture['team_name'],
        fixture['question_id'],
        blurb_cache_period(),
    )
    cache.invalidate(cache._generate_key('explain', logical))
    with patch('agent_service.get_or_calculate_rankings', return_value=_rankings()):
        with patch('agent_service.urllib.request.urlopen') as opened:
            response = client.post('/agent/explain', json={
                'team_name': fixture['team_name'],
                'year': fixture['year'],
                'week': fixture['week'],
                'question_id': fixture['question_id'],
                'provider': 'xai',
            })
    assert response.status_code == 200
    body = response.get_json()
    assert body['busy'] is True
    assert body['capped'] is True
    assert body['message'] == 'Busy right now. Try again later.'
    assert body['code'] == 'xai_weekly_usd'
    opened.assert_not_called()


def test_xai_explain_stops_on_daily_zero_when_the_week_cap_fits(client, monkeypatch):
    fixture = _load('xai_repeat_explain.json')
    monkeypatch.setenv('AI_MODE', 'live')
    monkeypatch.setenv('XAI_ENABLED', '1')
    monkeypatch.setenv('XAI_MAX_CALLS', '5')
    monkeypatch.setenv('XAI_WEEKLY_USD_CAP', '4')
    monkeypatch.setenv('AI_XAI_HOST', 'ai.xai')
    monkeypatch.delenv('AI_KILL', raising=False)
    monkeypatch.delenv('XAI_KILL', raising=False)
    monkeypatch.delenv('SPEND_GATE_HOST', raising=False)
    from agent_service import explain_cache_logical
    from cache import get_cache
    from shareable_blurb import blurb_cache_period
    from spend_guards import reset_xai_week_spend, xai_week_micros

    reset_xai_week_spend()
    cache = get_cache()
    logical = explain_cache_logical(
        'xai',
        fixture['year'],
        fixture['week'],
        fixture['team_name'],
        fixture['question_id'],
        blurb_cache_period(),
    )
    cache.invalidate(cache._generate_key('explain', logical))
    with patch('agent_service.get_or_calculate_rankings', return_value=_rankings()):
        with patch('agent_service.urllib.request.urlopen') as opened:
            response = client.post('/agent/explain', json={
                'team_name': fixture['team_name'],
                'year': fixture['year'],
                'week': fixture['week'],
                'question_id': fixture['question_id'],
                'provider': 'xai',
            })
    assert response.status_code == 200
    body = response.get_json()
    assert body['busy'] is True
    assert body['message'] == 'Busy right now. Try again later.'
    assert body['code'] == 'xai_budget'
    assert xai_week_micros() == 0
    opened.assert_not_called()
    reset_xai_week_spend()


def test_retired_name_detector_trips_on_planted_text():
    planted = ''.join(chr(code) for code in (109, 105, 110, 105, 109, 97, 120))
    assert contains_retired_name(f'the old client was {planted}')
    assert not contains_retired_name('xAI and Workers AI')


def test_retired_name_scan_excludes_only_purpose():
    planted = ''.join(chr(code) for code in (109, 105, 110, 105, 109, 97, 120))
    assert canon_scan_exclusions() == ('PURPOSE.md',)
    lines = [
        f'PURPOSE.md:47: stub, {planted}, Lean Pure',
        f'README.md:3: {planted}',
        f'worker/src/index.ts:1: {planted}',
    ]
    assert filter_retired_name_hits(lines) == lines[1:]
    assert all(not hit.startswith('PURPOSE.md:') for hit in retired_name_hits())


@pytest.mark.parametrize('fixture_name', [
    'workers_ai_repeat_explain.json',
])
def test_repeat_explain_makes_one_paid_call(client, monkeypatch, fixture_name):
    fixture = _load(fixture_name)
    provider = fixture['provider']
    monkeypatch.setenv('AI_MODE', 'live')
    monkeypatch.setenv('XAI_MAX_CALLS', '5')
    monkeypatch.setenv('AI_MAX_CALLS', '5')
    monkeypatch.delenv('AI_KILL', raising=False)
    monkeypatch.delenv('XAI_KILL', raising=False)
    monkeypatch.delenv('WORKERS_AI_KILL', raising=False)
    monkeypatch.delenv('SPEND_GATE_HOST', raising=False)
    monkeypatch.setenv('AI_XAI_HOST', 'ai.xai')
    monkeypatch.setenv('AI_WORKERS_HOST', 'ai.workers')
    from agent_service import explain_cache_logical
    from cache import get_cache
    from shareable_blurb import blurb_cache_period

    cache = get_cache()
    logical = explain_cache_logical(
        provider,
        fixture['year'],
        fixture['week'],
        fixture['team_name'],
        fixture['question_id'],
        blurb_cache_period(),
    )
    cache.invalidate(cache._generate_key('explain', logical))
    calls = []

    def fake_urlopen(req, timeout=60):
        calls.append(req.full_url)
        return _Response({'ok': True, 'text': fixture['answer']})

    payload = {
        'team_name': fixture['team_name'],
        'year': fixture['year'],
        'week': fixture['week'],
        'question_id': fixture['question_id'],
        'provider': provider,
    }
    with patch('agent_service.get_or_calculate_rankings', return_value=_rankings()):
        with patch('agent_service.urllib.request.urlopen', side_effect=fake_urlopen):
            first = client.post('/agent/explain', json=payload)
            second = client.post('/agent/explain', json=payload)
    assert first.status_code == 200
    assert second.status_code == 200
    assert first.get_json()['cached'] is False
    assert second.get_json()['cached'] is True
    assert second.get_json()['explanation'] == fixture['answer']
    host = 'ai.xai' if provider == 'xai' else 'ai.workers'
    assert calls == [f'http://{host}/complete']


def test_provider_kill_serves_stub_for_each_path(client, monkeypatch):
    fixture = _load('provider_kill.json')
    monkeypatch.setenv('AI_MODE', 'live')
    monkeypatch.setenv('AI_KILL', fixture['AI_KILL'])
    monkeypatch.setenv('XAI_KILL', fixture['XAI_KILL'])
    monkeypatch.setenv('WORKERS_AI_KILL', fixture['WORKERS_AI_KILL'])
    monkeypatch.setenv('XAI_MAX_CALLS', '5')
    monkeypatch.setenv('AI_MAX_CALLS', '5')
    monkeypatch.setenv('AI_XAI_HOST', 'ai.xai')
    monkeypatch.setenv('AI_WORKERS_HOST', 'ai.workers')
    with patch('agent_service.urllib.request.urlopen') as opened:
        with patch('agent_service.get_or_calculate_rankings', return_value=_rankings()):
            for provider, question_id in (('xai', 'results'), ('workers_ai', 'neighbors')):
                response = client.post('/agent/explain', json={
                    'team_name': 'Georgia',
                    'year': 2024,
                    'week': 10,
                    'question_id': question_id,
                    'provider': provider,
                })
                assert response.status_code == 200
                body = response.get_json()
                assert body['busy'] is True
                assert body['code'] == 'kill_switch'
                assert body['explanation']
    opened.assert_not_called()


def test_question_allowlist_is_the_four_phil_cleared():
    from agent_service import EXPLAIN_QUESTIONS, NO_PREDICTION_RULE, _explain_prompt

    assert tuple(EXPLAIN_QUESTIONS) == ('why_here', 'path_up', 'results', 'neighbors')
    for question in EXPLAIN_QUESTIONS.values():
        assert NO_PREDICTION_RULE in _explain_prompt({'team_name': 'Oregon'}, question)


def _post_live_explain(client, monkeypatch, answer: str, question_id: str = 'why_here'):
    monkeypatch.setenv('AI_MODE', 'live')
    monkeypatch.setenv('AI_MAX_CALLS', '5')
    monkeypatch.setenv('XAI_MAX_CALLS', '0')
    monkeypatch.delenv('AI_KILL', raising=False)
    monkeypatch.delenv('WORKERS_AI_KILL', raising=False)
    monkeypatch.delenv('SPEND_GATE_HOST', raising=False)
    monkeypatch.setenv('AI_WORKERS_HOST', 'ai.workers')
    from agent_service import explain_cache_logical
    from cache import get_cache
    from shareable_blurb import blurb_cache_period
    from spend_guards import reset_provider_call_counts

    reset_provider_call_counts()
    cache = get_cache()
    logical = explain_cache_logical(
        'workers_ai', 2024, 10, 'Oregon', question_id, blurb_cache_period(),
    )
    cache_key = cache._generate_key('explain', logical)
    cache.invalidate(cache_key)

    def fake_urlopen(req, timeout=60):
        return _Response({'ok': True, 'text': answer})

    payload = {
        'team_name': 'Oregon',
        'year': 2024,
        'week': 10,
        'question_id': question_id,
        'provider': 'workers_ai',
    }
    return cache, cache_key, payload, fake_urlopen


def test_grounded_answer_passes_and_inventions_serve_string_10(client, monkeypatch):
    from agent_service import EXPLAIN_BREAKDOWN

    grounded = 'Oregon is 9-0 after beating Ohio State.'
    planted = {
        'number': 'Oregon is 12-0 after beating Ohio State.',
        'team': 'Oregon beat Ohio State. Alabama sits nearby.',
        'game': 'Oregon lost to Ohio State.',
    }
    cache, cache_key, payload, fake_urlopen = _post_live_explain(client, monkeypatch, grounded)
    with patch('agent_service.get_or_calculate_rankings', return_value=_rankings()):
        with patch('agent_service.urllib.request.urlopen', side_effect=fake_urlopen):
            passed = client.post('/agent/explain', json=payload)
    assert passed.status_code == 200
    body = passed.get_json()
    assert body['explanation'] == grounded
    assert body['ai_written'] is True
    assert body['cached'] is False
    assert cache.get(cache_key)['explanation'] == grounded

    for name, answer in planted.items():
        cache.invalidate(cache_key)
        _cache, _key, _payload, opener = _post_live_explain(client, monkeypatch, answer)
        calls = []

        def fake_urlopen(req, timeout=60, _calls=calls, _answer=answer):
            _calls.append(req.full_url)
            return _Response({'ok': True, 'text': _answer})

        with patch('agent_service.get_or_calculate_rankings', return_value=_rankings()):
            with patch('agent_service.urllib.request.urlopen', side_effect=fake_urlopen):
                failed = client.post('/agent/explain', json=payload)
                again = client.post('/agent/explain', json=payload)
        assert failed.status_code == 200, name
        assert failed.get_json()['explanation'] == EXPLAIN_BREAKDOWN, name
        assert failed.get_json()['ai_written'] is False
        assert cache.get(cache_key) is None, name
        assert again.get_json()['explanation'] == EXPLAIN_BREAKDOWN
        assert len(calls) == 2, name


def test_real_2024_week_15_oregon_answers_pass_and_inventions_fail():
    rankings = json.loads(
        (ROOT / 'frontend' / 'static' / 'rankings' / '2024' / 'week-15.json').read_text()
    )
    from agent_service import _build_team_context, _explain_prompt, answer_is_grounded

    context = _build_team_context(rankings, 'Oregon')
    assert context is not None
    assert context['games'] == []
    records = context['records']
    answers = [
        f"{context['team_name']} sits #{context['rank']} in the {context['conference']}.",
        f"{context['team_name']}'s Team Quality is {int(context['team_quality_score'])}.",
        (
            f"Record Score and Conference Quality sit with Team Quality "
            f"for {context['team_name']}."
        ),
        f"{context['neighbor_behind']} is next to {context['team_name']}.",
        (
            f"Quality wins: {context['quality_wins']}. "
            f"Record: {records['total_wins']}-{records['total_losses']}."
        ),
    ]
    assert len(answers) >= 5
    for answer in answers:
        assert answer_is_grounded(answer, context), answer
    assert answer_is_grounded(
        "The formula is 80% Team Quality + 15% Record Score + 5% Conference Quality.",
        context,
    )
    beat_neighbor = f"{context['team_name']} beat {context['neighbor_behind']}."
    top_wins = {
        str(name).strip().lower()
        for name in (context.get('top_quality_wins') or [])
    }
    neighbor = str(context.get('neighbor_behind') or '').strip().lower()
    if neighbor and neighbor in top_wins:
        assert answer_is_grounded(beat_neighbor, context), beat_neighbor
    else:
        assert not answer_is_grounded(beat_neighbor, context), beat_neighbor
    assert not answer_is_grounded('Oregon lost to Ohio State.', context)
    assert not answer_is_grounded('Oregon is 15-0.', context)
    assert not answer_is_grounded('Oregon is 40-0.', context)
    assert not answer_is_grounded('Alabama sits nearby.', context)
    prompt = _explain_prompt(context, 'Which results are carrying this rank?')
    assert 'This context has no played-game list.' in prompt
    played = dict(context)
    played['games'] = [{'opponent': 'Ohio State', 'result': 'win'}]
    assert 'listed in games' in _explain_prompt(played, 'Which results are carrying this rank?')
    assert not answer_is_grounded('Oregon lost to Ohio State.', played)


def test_stub_explain_is_not_cached(client, monkeypatch):
    monkeypatch.setenv('AI_MODE', 'stub')
    from agent_service import explain_cache_logical
    from cache import get_cache
    from shareable_blurb import blurb_cache_period

    cache = get_cache()
    logical = explain_cache_logical(
        'stub', 2024, 10, 'Oregon', 'why_here', blurb_cache_period(),
    )
    cache_key = cache._generate_key('explain', logical)
    cache.invalidate(cache_key)
    with patch('agent_service.get_or_calculate_rankings', return_value=_rankings()):
        first = client.post('/agent/explain', json={
            'team_name': 'Oregon', 'year': 2024, 'week': 10, 'question_id': 'why_here',
        })
        second = client.post('/agent/explain', json={
            'team_name': 'Oregon', 'year': 2024, 'week': 10, 'question_id': 'why_here',
        })
    assert first.status_code == 200
    assert first.get_json()['ai_written'] is False
    assert second.get_json()['cached'] is False
    assert cache.get(cache_key) is None
