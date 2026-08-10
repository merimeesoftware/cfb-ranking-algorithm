"""Agent endpoints for ranking explanations and CFBD MCP proxy."""
import os
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
from spend_guards import (
    AIBudgetError,
    AIRateLimitError,
    check_agent_rate_limit,
    is_cfbd_offline,
    register_live_ai_call,
    resolve_ai_mode,
    spend_status,
)

# In-season daily / offseason monthly — keep TTL past the period boundary
TTL_BLURB_IN_SEASON = 36 * 60 * 60
TTL_BLURB_OFFSEASON = 40 * 24 * 60 * 60

agent_bp = Blueprint('agent', __name__, url_prefix='/agent')

_data_processor = None


def set_data_processor(processor) -> None:
    global _data_processor
    _data_processor = processor


CFBD_MCP_URL = os.environ.get('CFBD_MCP_URL', '')
MINIMAX_API_KEY = os.environ.get('MINIMAX_API_KEY', '')
MINIMAX_BASE_URL = os.environ.get('MINIMAX_BASE_URL', 'https://api.minimax.io/anthropic')
MINIMAX_MODEL = os.environ.get('MINIMAX_MODEL', 'MiniMax-M2.7')
# Blurbs are short; prefer M3 with thinking off so output isn't eaten by reasoning tokens
MINIMAX_BLURB_MODEL = os.environ.get('MINIMAX_BLURB_MODEL', 'MiniMax-M3')


def _require_agent_route(f):
    """Allow stub/off without MiniMax; live/MCP still need config when used."""
    @wraps(f)
    def decorated(*args, **kwargs):
        return f(*args, **kwargs)
    return decorated


def _client_key() -> str:
    forwarded = request.headers.get('X-Forwarded-For', '')
    if forwarded:
        return forwarded.split(',')[0].strip()
    return request.remote_addr or 'unknown'


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
            'path_to_climb': compute_path_to_climb(team, team_above),
        }
    return None


def _call_minimax(
    prompt: str,
    *,
    max_tokens: int = 1024,
    model: Optional[str] = None,
    disable_thinking: bool = False,
) -> str:
    """Call MiniMax via Anthropic-compatible API (paygo key — not Coding Plan)."""
    if not MINIMAX_API_KEY:
        return 'MiniMax API key not configured. Structured ranking context is available in the response.'

    call_n = register_live_ai_call()
    print(f'AI LIVE prompt #{call_n} (budget {ai_max_display()})')
    try:
        payload: Dict[str, Any] = {
            'model': model or MINIMAX_MODEL,
            'max_tokens': max_tokens,
            'messages': [{'role': 'user', 'content': prompt}],
        }
        if disable_thinking:
            payload['thinking'] = {'type': 'disabled'}
        # MiniMax Anthropic-compatible route prefers Authorization: Bearer;
        # keep x-api-key as a secondary Anthropic-style header.
        response = requests.post(
            f"{MINIMAX_BASE_URL}/v1/messages",
            headers={
                'Authorization': f'Bearer {MINIMAX_API_KEY}',
                'x-api-key': MINIMAX_API_KEY,
                'anthropic-version': '2023-06-01',
                'content-type': 'application/json',
            },
            json=payload,
            timeout=60,
        )
        response.raise_for_status()
        data = response.json()
        content = data.get('content', [])
        if isinstance(content, list) and content:
            texts = [
                block.get('text', '').strip()
                for block in content
                if isinstance(block, dict)
                and block.get('type', 'text') == 'text'
                and block.get('text')
            ]
            if texts:
                return '\n'.join(texts)
            # Fallback: any block with a text field (some MiniMax payloads omit type)
            texts = [
                block.get('text', '').strip()
                for block in content
                if isinstance(block, dict) and block.get('text')
            ]
            if texts:
                return '\n'.join(texts)
        return 'LLM explanation unavailable: empty text content'
    except AIBudgetError:
        raise
    except Exception as e:
        return f'LLM explanation unavailable: {e}'


def ai_max_display() -> str:
    from spend_guards import ai_max_calls
    max_c = ai_max_calls()
    return str(max_c) if max_c is not None else 'unlimited'


def _resolve_explanation(context: Dict[str, Any], question: str) -> tuple[Optional[str], str]:
    """Return (explanation, ai_mode)."""
    mode = resolve_ai_mode()
    if mode == 'off':
        return None, mode
    if mode == 'stub':
        return stub_explain_from_context(context, question), mode
    if not MINIMAX_API_KEY:
        return stub_explain_from_context(context, question), 'stub'
    prompt = (
        f"You are a college football ranking analyst. Answer concisely using ONLY the data provided.\n\n"
        f"Question: {question}\n\n"
        f"Team context (JSON): {context}\n\n"
        f"Formula: {int(round(FRS_WEIGHTS[0] * 100))}% Team Quality + "
        f"{int(round(FRS_WEIGHTS[1] * 100))}% Record Score + "
        f"{int(round(FRS_WEIGHTS[2] * 100))}% Conference Quality."
    )
    try:
        return _call_minimax(prompt), mode
    except AIBudgetError as e:
        stub = stub_explain_from_context(context, question)
        return f'{stub} [{e}]', 'stub'


@agent_bp.route('/health', methods=['GET'])
def agent_health():
    return jsonify({
        'status': 'ok',
        'minimax_configured': bool(MINIMAX_API_KEY),
        'cfbd_mcp_configured': bool(CFBD_MCP_URL),
        **spend_status(),
    })


@agent_bp.route('/explain', methods=['POST'])
@_require_agent_route
def explain_ranking():
    """
    Explain why a team is ranked where it is.

    Body: { "team_name": "Georgia", "year": 2024, "week": 10, "question": "optional" }
    AI_MODE=off → explanation null + context; stub → template; live → MiniMax (budgeted).
    """
    if _data_processor is None:
        return jsonify({'error': 'Data processor not initialized'}), 503

    try:
        check_agent_rate_limit(_client_key())
    except AIRateLimitError as e:
        return jsonify({'error': str(e), **spend_status()}), 429

    body = request.get_json(silent=True) or {}
    team_name = body.get('team_name') or request.args.get('team_name')
    year = int(body.get('year') or request.args.get('year', 2024))
    week = body.get('week') or request.args.get('week')
    week = int(week) if week is not None else None
    question = body.get('question', f'Why is {team_name} ranked where they are?')

    if not team_name:
        return jsonify({'error': 'team_name is required'}), 400

    # Offline: serve static/slim. Online: prefer full payload for wins_details.
    rankings = get_or_calculate_rankings(
        _data_processor,
        year,
        week,
        request.args,
        prefer_static=is_cfbd_offline(),
    )
    if not rankings:
        return jsonify({'error': f'No rankings data for {year}'}), 404

    context = _build_team_context(rankings, team_name)
    if not context:
        return jsonify({'error': f"Team '{team_name}' not found in rankings"}), 404

    explanation, mode = _resolve_explanation(context, question)

    return jsonify({
        'team_name': team_name,
        'year': year,
        'week': week,
        'context': context,
        'explanation': explanation,
        'ai_mode': mode,
        'formula': DEFAULT_CONFIG,
        'spend': spend_status(),
    })


BLURB_MAX_ATTEMPTS = 3


def _resolve_blurb(context: Dict[str, Any], kind: str = 'share') -> tuple[str, str]:
    """
    Return (blurb, ai_mode) for kind share|climb.

    Live MiniMax must produce ≤280 chars as-authored. Over-length drafts are
    rejected and rewritten (never chopped). Exhausted retries → stub.
    """
    stub_fn = stub_climb_blurb if kind == 'climb' else stub_shareable_blurb
    prompt_fn = build_climb_prompt if kind == 'climb' else build_blurb_prompt

    mode = resolve_ai_mode()
    if mode != 'live':
        return stub_fn(context), mode
    if not MINIMAX_API_KEY:
        return stub_fn(context), 'stub'

    previous = ''
    try:
        for attempt in range(BLURB_MAX_ATTEMPTS):
            if attempt == 0:
                prompt = prompt_fn(context)
            else:
                prompt = build_blurb_rewrite_prompt(previous, context, kind=kind)
            raw = _call_minimax(
                prompt,
                max_tokens=400,
                model=MINIMAX_BLURB_MODEL,
                disable_thinking=True,
            )
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
        return stub_fn(context), 'stub'


def _blurb_http(kind: str):
    """Shared handler for /agent/blurb and /agent/climb."""
    if _data_processor is None:
        return jsonify({'error': 'Data processor not initialized'}), 503

    try:
        check_agent_rate_limit(_client_key())
    except AIRateLimitError as e:
        return jsonify({'error': str(e), **spend_status()}), 429

    body = request.get_json(silent=True) or {}
    team_name = body.get('team_name') or request.args.get('team_name')
    year = int(body.get('year') or request.args.get('year', 2024))
    week = body.get('week') if 'week' in body else request.args.get('week')
    week = int(week) if week is not None and week != '' else None

    if not team_name:
        return jsonify({'error': 'team_name is required'}), 400

    period = blurb_cache_period()
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
            'spend': spend_status(),
        })

    rankings = get_or_calculate_rankings(
        _data_processor,
        year,
        week,
        request.args,
        prefer_static=is_cfbd_offline(),
    )
    if not rankings:
        return jsonify({'error': f'No rankings data for {year}'}), 404

    context = _build_team_context(rankings, team_name)
    if not context:
        return jsonify({'error': f"Team '{team_name}' not found in rankings"}), 404

    blurb, mode = _resolve_blurb(context, kind=kind)
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
    }
    ttl = TTL_BLURB_IN_SEASON if is_in_season() else TTL_BLURB_OFFSEASON
    cache.set(
        cache_key,
        {k: v for k, v in payload.items() if k != 'cached'},
        ttl,
        prefix=prefix,
    )

    return jsonify({
        **payload,
        'spend': spend_status(),
    })


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
