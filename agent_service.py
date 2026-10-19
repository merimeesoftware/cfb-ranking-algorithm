"""Agent endpoints for ranking explanations and CFBD MCP proxy."""
import json
import os
import re
import urllib.error
import urllib.request
from functools import wraps
from typing import Any, Dict, List, Optional

import requests
from flask import Blueprint, jsonify, request

from ai_stub import stub_explain_from_context
from cache import get_cache
from path_to_climb import compute_path_to_climb
from ranking_service import get_or_calculate_rankings, DEFAULT_CONFIG, FRS_WEIGHTS
from shareable_blurb import (
    BLURB_MAX_CHARS,
    blurb_cache_key,
    blurb_cache_period,
    build_blurb_prompt,
    build_blurb_rewrite_prompt,
    build_climb_prompt,
    clean_blurb_candidate,
    extract_blurb_text,
    is_in_season,
    stub_climb_blurb,
    stub_shareable_blurb,
)
from public_board import BUSY_MESSAGE, busy_body
from spend_guards import (
    AIBudgetError,
    AIRateLimitError,
    check_agent_rate_limit,
    guard_xai_spend,
    is_provider_killed,
    register_live_provider_call,
    resolve_ai_mode,
    resolve_ai_provider,
)
from static_rankings import (
    DEFAULT_ROOT,
    read_climb_blurbs,
    read_share_blurbs,
    team_blurb_from_static,
)

# In-season daily / offseason monthly — keep TTL past the period boundary
TTL_BLURB_IN_SEASON = 36 * 60 * 60
TTL_BLURB_OFFSEASON = 40 * 24 * 60 * 60

# Frontend static rankings (deployed with SPA) then repo static_rankings/
_FRONTEND_STATIC = os.path.join(os.path.dirname(__file__), 'frontend', 'static', 'rankings')

agent_bp = Blueprint('agent', __name__, url_prefix='/agent')

_data_processor = None


def set_data_processor(processor) -> None:
    global _data_processor
    _data_processor = processor


CFBD_MCP_URL = os.environ.get('CFBD_MCP_URL', '')
PROVIDER_TIMEOUT = int(os.environ.get('AI_PROVIDER_TIMEOUT', '60'))

# Fixed prompts. Free-text questions are rejected.
# String 10 stays the curly apostrophe already locked in the visitor UI.
EXPLAIN_BREAKDOWN = 'Couldn\u2019t break down this ranking right now.'
NO_PREDICTION_RULE = (
    'Answers describe only results already played, with no predictions, '
    'picks, odds or forward-looking verbs.'
)
EXPLAIN_QUESTIONS = {
    'why_here': 'Why is this team ranked here?',
    'path_up': "What's holding them back?",
    'results': 'Which results are carrying this rank?',
    'neighbors': 'Why this team and not the ones next to it?',
}


class ProviderUnconfigured(RuntimeError):
    """The Worker host for this provider is not set."""


def _require_agent_route(f):
    """Allow stub/off without a live provider; live still needs the Worker host."""
    @wraps(f)
    def decorated(*args, **kwargs):
        return f(*args, **kwargs)
    return decorated


def _client_key() -> str:
    """Visitor identity from Cloudflare. X-Forwarded-For is not trusted."""
    connecting = (request.headers.get('CF-Connecting-IP') or '').strip()
    return connecting or 'unknown'


def _busy(code: str):
    return jsonify(busy_body(code)), 429


def _top_quality_wins(team: Dict[str, Any], limit: int = 3) -> List[str]:
    """Extract up to `limit` quality-win opponent names from wins_details."""
    wins = team.get('wins_details') or []
    names: List[str] = []
    for win in wins:
        if not win.get('is_quality_win'):
            continue
        opp = win.get('opponent')
        if opp:
            names.append(opp)
        if len(names) >= limit:
            break
    return names


def _build_team_context(rankings: Dict[str, Any], team_name: str) -> Optional[Dict[str, Any]]:
    team_rankings = rankings.get('team_rankings', [])
    for i, team in enumerate(team_rankings):
        if team['team_name'].lower() != team_name.lower():
            continue

        team_above = team_rankings[i - 1] if i > 0 else None
        team_below = team_rankings[i + 1] if i + 1 < len(team_rankings) else None
        tq = float(team.get('team_quality_score') or 0)
        rec = float(team.get('record_score') or 0)
        cq = float(team.get('conference_quality_score') or 0)

        return {
            'rank': i + 1,
            'team_name': team['team_name'],
            'conference': team['conference'],
            'final_ranking_score': team['final_ranking_score'],
            'team_quality_score': team['team_quality_score'],
            'record_score': team['record_score'],
            'conference_quality_score': team['conference_quality_score'],
            'formula_breakdown': {
                'tq_contribution': round(tq * FRS_WEIGHTS[0], 2),
                'rec_contribution': round(rec * FRS_WEIGHTS[1], 2),
                'cq_contribution': round(cq * FRS_WEIGHTS[2], 2),
                'total': team.get('final_ranking_score'),
            },
            'records': team.get('records', {}),
            'sos': team.get('sos'),
            'sov': team.get('sov'),
            'quality_wins': team.get('quality_wins'),
            'quality_losses': team.get('quality_losses'),
            'bad_losses': team.get('bad_losses'),
            'top_quality_wins': _top_quality_wins(team),
            'neighbor_ahead': team_above['team_name'] if team_above else None,
            'neighbor_behind': team_below['team_name'] if team_below else None,
            'games': _played_games(team),
            'path_to_climb': compute_path_to_climb(team, team_above),
        }
    return None


def explain_cache_logical(
    provider: str,
    year: int,
    week: Optional[int],
    team_name: str,
    question_id: str,
    period: str,
) -> str:
    """explain:{provider}:{year}:{week}:{team}:{question_id}:{period}"""
    week_part = 'none' if week is None else str(week)
    team = team_name.strip().lower()
    return f'explain:{provider}:{year}:{week_part}:{team}:{question_id}:{period}'


def _provider_host(provider: str) -> str:
    name = 'AI_XAI_HOST' if provider == 'xai' else 'AI_WORKERS_HOST'
    return os.environ.get(name, '').strip()


def _budget_code(provider: str, exc: AIBudgetError) -> str:
    if is_provider_killed(provider):
        return 'kill_switch'
    return exc.code or f'{provider}_budget'


def _call_provider(provider: str, prompt: str) -> str:
    """Ask the Worker host for one completion. The credential stays on the Worker."""
    if provider not in ('xai', 'workers_ai'):
        raise AIBudgetError(f'Unknown AI provider: {provider}')
    if is_provider_killed(provider):
        raise AIBudgetError('AI kill switch is on.', code='kill_switch')
    if provider == 'xai':
        guard_xai_spend(prompt, commit=False)
    host = _provider_host(provider)
    if not host:
        raise ProviderUnconfigured(provider)
    reserved = False
    if provider == 'xai':
        reserved = guard_xai_spend(prompt, commit=True)
    call_n = register_live_provider_call(provider)
    print(f'AI LIVE prompt #{call_n} provider={provider}')
    payload = json.dumps({
        'messages': [{'role': 'user', 'content': prompt}],
    }).encode()
    headers = {'content-type': 'application/json'}
    if reserved:
        headers['x-xai-week-reserved'] = '1'
    if provider == 'workers_ai' and os.environ.get('SPEND_GATE_HOST', '').strip():
        headers['x-workers-ai-reserved'] = '1'
    req = urllib.request.Request(
        f'http://{host}/complete',
        data=payload,
        headers=headers,
        method='POST',
    )
    try:
        with urllib.request.urlopen(req, timeout=PROVIDER_TIMEOUT) as resp:
            data = json.loads(resp.read().decode() or '{}')
    except AIBudgetError:
        raise
    except urllib.error.HTTPError as exc:
        try:
            data = json.loads(exc.read().decode() or '{}')
        except (json.JSONDecodeError, OSError):
            data = {}
        if data.get('code') in ('kill_switch', 'xai_weekly_usd') or exc.code == 429:
            raise AIBudgetError(
                'AI kill switch or budget denied the live call.',
                code=data.get('code') or None,
            ) from exc
        return 'LLM explanation unavailable: upstream'
    except (urllib.error.URLError, TimeoutError, json.JSONDecodeError, OSError) as exc:
        return f'LLM explanation unavailable: {exc}'
    text = (data.get('text') or '').strip() if isinstance(data, dict) else ''
    if data.get('ok') and text:
        return text
    return 'LLM explanation unavailable: empty text content'


def _played_games(team: Dict[str, Any]) -> List[Dict[str, str]]:
    """Wins and losses already on the server payload. No future games."""
    games: List[Dict[str, str]] = []
    for result, key in (('win', 'wins_details'), ('loss', 'losses_details')):
        for row in team.get(key) or []:
            if not isinstance(row, dict):
                continue
            opponent = row.get('opponent')
            if isinstance(opponent, str) and opponent.strip():
                games.append({'opponent': opponent.strip(), 'result': result})
    return games


def _number_token(raw: str) -> str:
    if '.' in raw:
        value = float(raw)
        if value.is_integer():
            return str(int(value))
        return format(value, 'f').rstrip('0').rstrip('.')
    return str(int(raw))


def _payload_facts(payload: Dict[str, Any]) -> tuple[set[str], set[str], set[tuple[str, str]]]:
    numbers: set[str] = set()
    names: set[str] = set()
    games: set[tuple[str, str]] = set()

    def walk(value: Any) -> None:
        if isinstance(value, bool) or value is None:
            return
        if isinstance(value, (int, float)):
            numbers.add(_number_token(str(value) if isinstance(value, int) else format(value, 'f')))
            return
        if isinstance(value, str):
            text = value.strip()
            if any(char.isalpha() for char in text):
                names.add(text.lower())
            for match in re.findall(r'\d+(?:\.\d+)?', text):
                numbers.add(_number_token(match))
            return
        if isinstance(value, dict):
            for item in value.values():
                walk(item)
        elif isinstance(value, list):
            for item in value:
                walk(item)

    walk(payload)
    for game in payload.get('games') or []:
        if not isinstance(game, dict):
            continue
        opponent = game.get('opponent')
        result = game.get('result')
        if isinstance(opponent, str) and result in ('win', 'loss'):
            games.add((result, opponent.strip().lower()))
            names.add(opponent.strip().lower())
    return numbers, names, games


_NAME_SPAN = re.compile(
    r"[A-Z][A-Za-z&'-]*(?:\s+[A-Z][A-Za-z&'-]*)*"
)
_FORMULA_LABELS = ('Team Quality', 'Record Score', 'Conference Quality')
_EXACT_FORMULA = re.compile(
    '|'.join(
        rf'\b{int(round(float(weight) * 100))}%\s+{re.escape(label)}\b'
        for weight, label in zip(FRS_WEIGHTS, _FORMULA_LABELS)
    )
)
_RECORD_PAIR = re.compile(r'\b(\d+)\s*[-\u2010-\u2015\u2212]\s*(\d+)\b')
_RESULT_WORD = re.compile(
    r'\b(?:head-to-head|knocked off|took down|defeat(?:ed|s)?|victory|against|'
    r'routed|dominated|handled|outlasted|met|played|stomped|'
    r'wins?|won|winning|losses|loss|lost|losing|results?|'
    r'beats?|beating|beaten|fell|topped|edged|edge|upset|downed|over)\b',
    re.IGNORECASE,
)
_LOSS_WORD = re.compile(
    r'\b(?:losses|loss|lost|losing|fell)\b',
    re.IGNORECASE,
)
_POSITION_WORD = re.compile(
    r'\b(?:next to|ahead|behind|above|below|spot|place|ranked|sits)\b',
    re.IGNORECASE,
)
_TOP_WIN_PHRASE = re.compile(r'\bbeat\b|\bwin over\b', re.IGNORECASE)
_NOT_A_TEAM = {
    'the', 'they', 'their', 'this', 'that', 'these', 'those', 'record',
    'quality', 'notable', 'immediately', 'a', 'an', 'after', 'before',
    'with', 'from', 'and', 'but', 'or', 'on', 'in', 'at', 'for', 'to',
}
# Terms the explainer states. They are not team names.
_EXPLAINER_TERMS = {
    'team quality',
    'record score',
    'conference quality',
    'final ranking score',
    'quality wins',
    'quality losses',
    'bad losses',
    'strength of schedule',
    'strength of victory',
}


def _record_pairs(records: Any) -> set[tuple[str, str]]:
    """Total and conference win-loss pairs. Other splits are not a record."""
    if not isinstance(records, dict):
        return set()
    pairs: set[tuple[str, str]] = set()
    for wins_key, losses_key in (
        ('total_wins', 'total_losses'),
        ('conf_wins', 'conf_losses'),
    ):
        wins = records.get(wins_key)
        losses = records.get(losses_key)
        if isinstance(wins, bool) or isinstance(losses, bool):
            continue
        if isinstance(wins, int) and isinstance(losses, int):
            pairs.add((str(wins), str(losses)))
    return pairs


def _strip_possessive(name: str) -> str:
    text = name.strip().lower()
    for suffix in ("'s", '\u2019s'):
        if text.endswith(suffix):
            return text[: -len(suffix)].strip()
    return text


def _context_teams(payload: Dict[str, Any]) -> set[str]:
    teams: set[str] = set()

    def add(value: Any) -> None:
        if isinstance(value, str) and value.strip():
            teams.add(_strip_possessive(value))

    add(payload.get('team_name'))
    add(payload.get('neighbor_ahead'))
    add(payload.get('neighbor_behind'))
    for name in payload.get('top_quality_wins') or []:
        add(name)
    for game in payload.get('games') or []:
        if isinstance(game, dict):
            add(game.get('opponent'))
    return teams


def _sentences(text: str) -> list[str]:
    return [part.strip() for part in re.split(r'[.!?]+', text) if part.strip()]


def _spans_longer_team(text: str, start: int, end: int, roster: set[str]) -> bool:
    """True when this match is only the start of a longer roster name."""
    for other in roster:
        if len(other) <= end - start:
            continue
        stop = start + len(other)
        if stop > len(text) or text[start:stop] != other:
            continue
        if stop < len(text) and text[stop].isalnum():
            continue
        return True
    return False


def _whole_team_spans(text: str, team: str, roster: set[str]) -> list[tuple[int, int]]:
    spans: list[tuple[int, int]] = []
    for match in re.finditer(rf'\b{re.escape(team)}\b', text):
        if _spans_longer_team(text, match.start(), match.end(), roster):
            continue
        spans.append((match.start(), match.end()))
    return spans


def _mentioned_teams(text: str, teams: set[str]) -> set[str]:
    lowered = re.sub(r"['\u2019]s\b", '', text, flags=re.IGNORECASE).lower()
    found: set[str] = set()
    for team in sorted(teams, key=len, reverse=True):
        spans = _whole_team_spans(lowered, team, teams)
        if not spans:
            continue
        found.add(team)
        chars = list(lowered)
        for start, end in spans:
            for index in range(start, end):
                chars[index] = ' '
        lowered = ''.join(chars)
    return found


def _neighbor_names(payload: Dict[str, Any]) -> set[str]:
    names: set[str] = set()
    for key in ('neighbor_ahead', 'neighbor_behind'):
        value = payload.get(key)
        if isinstance(value, str) and value.strip():
            names.add(_strip_possessive(value))
    return names


def _neighbor_placement(sentence: str, others: set[str], neighbors: set[str]) -> bool:
    """A second team is allowed when the sentence only places neighbors.

    A result word anywhere in the sentence blocks it. A later position
    word does not split the sentence into a safe clause.
    """
    if not others or not others <= neighbors:
        return False
    if _RESULT_WORD.search(sentence):
        return False
    return _POSITION_WORD.search(sentence) is not None


def _subject_before_phrase(sentence: str, subject: str, roster: set[str]) -> bool:
    """The team being explained is the one that beat or won over.

    The subject has to be the whole team name. ``Ohio`` does not match
    ``Ohio State``, and ``Oregon`` does not match ``Oregon State``.
    """
    lowered = re.sub(r"['\u2019]s\b", '', sentence, flags=re.IGNORECASE).lower()
    match = _TOP_WIN_PHRASE.search(lowered)
    if match is None or not subject:
        return False
    prefix = lowered[:match.start()]
    return bool(_whole_team_spans(prefix, subject, roster))


def _top_win_exception(
    sentence: str,
    subject: str,
    others: set[str],
    top_wins: set[str],
) -> bool:
    """Subject beat or won over a top_quality_wins team, and nothing else."""
    if not others or not others <= top_wins:
        return False
    if not _subject_before_phrase(sentence, subject, top_wins | {subject} | others):
        return False
    remainder = _TOP_WIN_PHRASE.sub(' ', sentence)
    return _RESULT_WORD.search(remainder) is None


def answer_is_grounded(answer: str, payload: Dict[str, Any]) -> bool:
    """Every number and team name in the answer is in the payload.

    Only the three FRS weight phrases are removed before the number check.
    Any other percent fails. An N-M pair, including a Unicode dash, is
    accepted only when it is the total record or the conference record.
    With no games list, a sentence that names another payload team passes
    only when every other team is a neighbor, the sentence has a position
    word, and it has no result word anywhere in it. The exception is the
    subject team beating or winning over a top_quality_wins team, matched
    on the whole team name. A result word in the next sentence fails too.
    When games are listed, that result has to be one of them. An N-M pair
    may use a Unicode dash or a minus sign.
    """
    text = (answer or '').strip()
    if not text or text.startswith('LLM explanation unavailable'):
        return False
    numbers, names, games = _payload_facts(payload)
    counted = _EXACT_FORMULA.sub(' ', text)
    if '%' in counted:
        return False
    for raw in re.findall(r'\d+(?:\.\d+)?', counted):
        if _number_token(raw) not in numbers:
            return False
    allowed_records = _record_pairs(payload.get('records'))
    for wins, losses in _RECORD_PAIR.findall(text):
        if (wins, losses) not in allowed_records:
            return False
    named = re.sub(r"['\u2019]s\b", '. ', text, flags=re.IGNORECASE)
    for span in _NAME_SPAN.findall(named):
        normalized = _strip_possessive(span)
        if normalized in _NOT_A_TEAM or normalized in _EXPLAINER_TERMS:
            continue
        if normalized not in names:
            return False
    subject = _strip_possessive(str(payload.get('team_name') or ''))
    roster = _context_teams(payload)
    top_wins = {
        _strip_possessive(name)
        for name in (payload.get('top_quality_wins') or [])
        if isinstance(name, str) and name.strip()
    }
    played = bool(payload.get('games'))
    neighbors = _neighbor_names(payload)
    previous_named_other = False
    for sentence in _sentences(text):
        if previous_named_other and _RESULT_WORD.search(sentence):
            return False
        others = _mentioned_teams(sentence, roster) - {subject}
        previous_named_other = bool(others)
        if not others:
            continue
        if not played:
            if _top_win_exception(sentence, subject, others, top_wins):
                continue
            if _neighbor_placement(sentence, others, neighbors):
                continue
            return False
        if _RESULT_WORD.search(sentence) is None:
            continue
        kind = 'loss' if _LOSS_WORD.search(sentence) else 'win'
        if any((kind, team) not in games for team in others):
            return False
    return True


def _explain_prompt(context: Dict[str, Any], question: str) -> str:
    w_tq, w_rec, w_cq = FRS_WEIGHTS
    if context.get('games'):
        facts = 'scores, records, and games'
        game_rule = (
            'Name a game result only when that opponent and result are listed in games.'
        )
    else:
        facts = 'scores and records'
        game_rule = 'Do not claim who beat whom. This context has no played-game list.'
    return (
        'You are a college football ranking analyst. Answer concisely.\n'
        f'Use ONLY the Team context JSON for {facts}. Do not invent them.\n'
        f'{NO_PREDICTION_RULE}\n'
        f'{game_rule}\n'
        f'Question: {question}\n\n'
        f'Team context (JSON): {context}\n\n'
        f'Formula: {w_tq:.0%} Team Quality + {w_rec:.0%} Record Score + {w_cq:.0%} Conference Quality.'
    )


@agent_bp.route('/health', methods=['GET'])
def agent_health():
    # Budget, cap counters, and key-slot status stay off this public route.
    return jsonify({'status': 'ok'})


def _reject_question(body: Dict[str, Any]):
    if body.get('question'):
        return jsonify({
            'error': 'question is not accepted. Send an allowlisted question_id.',
            'code': 'question_id',
        }), 400
    question_id = body.get('question_id')
    if not isinstance(question_id, str) or question_id not in EXPLAIN_QUESTIONS:
        return jsonify({
            'error': 'question_id must be an allowlisted prompt.',
            'code': 'question_id',
        }), 400
    return None


def _reject_provider(body: Dict[str, Any], mode: str):
    raw = body.get('provider')
    if raw is None or (isinstance(raw, str) and not raw.strip()):
        if mode == 'live':
            return resolve_ai_provider(), None
        return 'stub', None
    if not isinstance(raw, str) or raw.strip().lower() not in ('xai', 'workers_ai'):
        return None, (jsonify({
            'error': 'provider must be xai or workers_ai.',
            'code': 'provider',
        }), 400)
    if mode != 'live':
        return 'stub', None
    return raw.strip().lower(), None


def _capped_explain(
    code: str,
    context: Dict[str, Any],
    team_name: str,
    year: int,
    week: Optional[int],
    question_id: str,
    provider: str,
):
    return jsonify({
        **busy_body(code),
        'team_name': team_name,
        'year': year,
        'week': week,
        'context': context,
        'explanation': stub_explain_from_context(context, EXPLAIN_QUESTIONS[question_id]),
        'ai_mode': 'stub',
        'question_id': question_id,
        'provider': provider,
        'cached': False,
        'formula': DEFAULT_CONFIG,
    })


@agent_bp.route('/explain', methods=['POST'])
@_require_agent_route
def explain_ranking():
    """
    Explain why a team is ranked where it is.

    Body: question_id (allowlisted), optional provider xai|workers_ai.
    Stub and off do not call a provider. Live calls are budgeted per provider.
    A repeat of the same cache key does not make another paid call.
    """
    if _data_processor is None:
        return jsonify({'error': 'Data processor not initialized'}), 503

    body = request.get_json(silent=True) or {}
    rejected = _reject_question(body)
    if rejected:
        return rejected
    question_id = body['question_id']
    mode = resolve_ai_mode()
    provider, provider_error = _reject_provider(body, mode)
    if provider_error:
        return provider_error

    try:
        check_agent_rate_limit(_client_key())
    except AIRateLimitError:
        return _busy('agent_rate_limit')

    team_name = body.get('team_name') or request.args.get('team_name')
    year = int(body.get('year') or request.args.get('year', 2024))
    week = body.get('week') if 'week' in body else request.args.get('week')
    week = int(week) if week is not None and week != '' else None
    if not team_name:
        return jsonify({'error': 'team_name is required'}), 400

    period = blurb_cache_period()
    cache = get_cache()
    logical = explain_cache_logical(provider, year, week, team_name, question_id, period)
    cache_key = cache._generate_key('explain', logical)
    killed = mode == 'live' and provider in ('xai', 'workers_ai') and is_provider_killed(provider)
    if not killed:
        cached = cache.get(cache_key)
        if isinstance(cached, dict) and 'explanation' in cached:
            return jsonify({**cached, 'cached': True})

    rankings = get_or_calculate_rankings(
        _data_processor,
        year,
        week,
        request.args,
        prefer_static=True,
        allow_compute=False,
    )
    if not rankings:
        return jsonify({'error': f'No rankings data for {year}'}), 404

    context = _build_team_context(rankings, team_name)
    if not context:
        return jsonify({'error': f"Team '{team_name}' not found in rankings"}), 404

    question = EXPLAIN_QUESTIONS[question_id]
    if killed:
        return _capped_explain(
            'kill_switch', context, team_name, year, week, question_id, provider,
        )
    if mode == 'off':
        explanation, served = None, 'off'
    elif mode == 'stub' or provider == 'stub':
        explanation, served = stub_explain_from_context(context, question), 'stub'
    else:
        try:
            explanation = _call_provider(provider, _explain_prompt(context, question))
            served = 'live'
        except ProviderUnconfigured:
            explanation, served = stub_explain_from_context(context, question), 'stub'
        except AIBudgetError as exc:
            return _capped_explain(
                _budget_code(provider, exc),
                context, team_name, year, week, question_id, provider,
            )

    ai_written = served == 'live' and answer_is_grounded(explanation or '', context)
    if served == 'live' and not ai_written:
        explanation = EXPLAIN_BREAKDOWN
    payload = {
        'team_name': team_name,
        'year': year,
        'week': week,
        'context': context,
        'explanation': explanation,
        'ai_mode': served,
        'ai_written': ai_written,
        'question_id': question_id,
        'provider': provider if ai_written else 'stub',
        'cached': False,
        'formula': DEFAULT_CONFIG,
    }
    if ai_written:
        ttl = TTL_BLURB_IN_SEASON if is_in_season() else TTL_BLURB_OFFSEASON
        cache.set(cache_key, payload, ttl, prefix='explain')
    return jsonify(payload)


BLURB_MAX_ATTEMPTS = 3


def _resolve_blurb(context: Dict[str, Any], kind: str = 'share') -> tuple[str, str]:
    """
    Return (blurb, ai_mode) for kind share|climb.

    Live text must be ≤280 chars as-authored. Over-length drafts are
    rejected and rewritten (never chopped). Exhausted retries → stub.
    """
    stub_fn = stub_climb_blurb if kind == 'climb' else stub_shareable_blurb
    prompt_fn = build_climb_prompt if kind == 'climb' else build_blurb_prompt

    mode = resolve_ai_mode()
    if mode != 'live':
        return stub_fn(context), mode
    provider = resolve_ai_provider()
    if is_provider_killed(provider):
        raise AIBudgetError('AI kill switch is on.')
    if not _provider_host(provider):
        return stub_fn(context), 'stub'

    previous = ''
    try:
        for attempt in range(BLURB_MAX_ATTEMPTS):
            if attempt == 0:
                prompt = prompt_fn(context)
            else:
                prompt = build_blurb_rewrite_prompt(previous, context, kind=kind)
            raw = _call_provider(provider, prompt)
            text = extract_blurb_text(raw)
            if text:
                return text, mode
            candidate = clean_blurb_candidate(raw)
            if candidate:
                previous = candidate
            elif not previous:
                previous = (raw or '')[:500]
        return stub_fn(context), 'stub'
    except AIBudgetError:
        raise


def _static_blurb_for_team(
    kind: str,
    year: int,
    week: Optional[int],
    team_name: str,
    period: str,
) -> Optional[str]:
    """Prefer frontend static share/climb JSON for the current period."""
    if week is None:
        return None
    readers = {
        'share': read_share_blurbs,
        'climb': read_climb_blurbs,
    }
    reader = readers.get(kind)
    if not reader:
        return None
    for root in (_FRONTEND_STATIC, DEFAULT_ROOT):
        payload = reader(year, week, root=root)
        text = team_blurb_from_static(payload, team_name, require_period=period)
        if text:
            return text
        # Lookback durability: accept any period if labeled lookback-*
        if payload and str(payload.get('period', '')).startswith('lookback-'):
            text = team_blurb_from_static(payload, team_name, require_period=None)
            if text:
                return text
    return None


def _blurb_http(kind: str):
    """Shared handler for /agent/blurb and /agent/climb."""
    if _data_processor is None:
        return jsonify({'error': 'Data processor not initialized'}), 503

    try:
        check_agent_rate_limit(_client_key())
    except AIRateLimitError:
        return _busy('agent_rate_limit')

    body = request.get_json(silent=True) or {}
    team_name = body.get('team_name') or request.args.get('team_name')
    year = int(body.get('year') or request.args.get('year', 2024))
    week = body.get('week') if 'week' in body else request.args.get('week')
    week = int(week) if week is not None and week != '' else None

    if not team_name:
        return jsonify({'error': 'team_name is required'}), 400

    period = blurb_cache_period()
    static_text = _static_blurb_for_team(kind, year, week, team_name, period)
    if static_text:
        return jsonify({
            'team_name': team_name,
            'year': year,
            'week': week,
            'kind': kind,
            'blurb': static_text,
            'max_chars': BLURB_MAX_CHARS,
            'ai_mode': 'static',
            'cache_period': period,
            'refresh': 'daily' if is_in_season() else 'monthly',
            'cached': True,
            'source': 'static',
        })

    cache = get_cache()
    prefix = f'{kind}_blurb'
    cache_key = cache._generate_key(
        prefix,
        blurb_cache_key(team_name, year, week, period, kind=kind),
    )
    cached = cache.get(cache_key)
    if isinstance(cached, dict) and cached.get('blurb'):
        return jsonify({
            **cached,
            'cached': True,
            'source': cached.get('source', 'cache'),
        })

    rankings = get_or_calculate_rankings(
        _data_processor,
        year,
        week,
        request.args,
        prefer_static=True,
        allow_compute=False,
    )
    if not rankings:
        return jsonify({'error': f'No rankings data for {year}'}), 404

    context = _build_team_context(rankings, team_name)
    if not context:
        return jsonify({'error': f"Team '{team_name}' not found in rankings"}), 404

    try:
        blurb, mode = _resolve_blurb(context, kind=kind)
    except AIBudgetError as exc:
        provider = resolve_ai_provider()
        code = _budget_code(provider, exc)
        stub = stub_climb_blurb(context) if kind == 'climb' else stub_shareable_blurb(context)
        return jsonify({
            **busy_body(code),
            'team_name': context['team_name'],
            'year': year,
            'week': week,
            'kind': kind,
            'blurb': stub,
            'ai_mode': 'stub',
            'provider': provider,
            'max_chars': BLURB_MAX_CHARS,
        })
    if len(blurb) > BLURB_MAX_CHARS:
        # Invariant: never serve a chopped or over-limit blurb
        blurb = stub_climb_blurb(context) if kind == 'climb' else stub_shareable_blurb(context)
        mode = 'stub'
    payload = {
        'team_name': context['team_name'],
        'year': year,
        'week': week,
        'kind': kind,
        'blurb': blurb,
        'max_chars': BLURB_MAX_CHARS,
        'ai_mode': mode,
        'cache_period': period,
        'refresh': 'daily' if is_in_season() else 'monthly',
        'cached': False,
        'source': 'live' if mode == 'live' else 'stub',
        'provider': resolve_ai_provider() if mode == 'live' else None,
    }
    ttl = TTL_BLURB_IN_SEASON if is_in_season() else TTL_BLURB_OFFSEASON
    cache.set(
        cache_key,
        {k: v for k, v in payload.items() if k != 'cached'},
        ttl,
        prefix=prefix,
    )

    return jsonify(payload)


@agent_bp.route('/blurb', methods=['GET', 'POST'])
@_require_agent_route
def shareable_blurb_route():
    """Shareable why-blurb (≤280 chars): ranking why + debate hook."""
    return _blurb_http('share')


@agent_bp.route('/climb', methods=['GET', 'POST'])
@_require_agent_route
def climb_blurb_route():
    """Path-to-climb blurb (≤280 chars): StoryBrand-simple chase narrative."""
    return _blurb_http('climb')


@agent_bp.route('/mcp/query', methods=['POST'])
def mcp_query():
    """
    Proxy ad-hoc queries to CFBD MCP sidecar (when CFBD_MCP_URL is set).
    Body: { "tool": "get-games", "params": { "year": 2024 } }
    """
    if not CFBD_MCP_URL:
        return jsonify({'error': 'CFBD MCP sidecar not configured (CFBD_MCP_URL)'}), 503

    body = request.get_json(silent=True) or {}
    tool = body.get('tool')
    params = body.get('params', {})
    if not tool:
        return jsonify({'error': 'tool is required'}), 400

    try:
        response = requests.post(
            f"{CFBD_MCP_URL.rstrip('/')}/tools/{tool}",
            json=params,
            timeout=30,
        )
        response.raise_for_status()
        return jsonify(response.json())
    except Exception as e:
        return jsonify({'error': f'MCP query failed: {e}'}), 502
