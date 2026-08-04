"""Agent endpoints for ranking explanations and CFBD MCP proxy."""
import os
from functools import wraps
from typing import Any, Dict, List, Optional

import requests
from flask import Blueprint, jsonify, request

from ai_stub import stub_explain_from_context
from path_to_climb import compute_path_to_climb
from ranking_service import get_or_calculate_rankings, DEFAULT_CONFIG
from spend_guards import (
    AIBudgetError,
    AIRateLimitError,
    check_agent_rate_limit,
    is_cfbd_offline,
    register_live_ai_call,
    resolve_ai_mode,
    spend_status,
)

agent_bp = Blueprint('agent', __name__, url_prefix='/agent')

_data_processor = None


def set_data_processor(processor) -> None:
    global _data_processor
    _data_processor = processor

CFBD_MCP_URL = os.environ.get('CFBD_MCP_URL', '')
MINIMAX_API_KEY = os.environ.get('MINIMAX_API_KEY', '')
MINIMAX_BASE_URL = os.environ.get('MINIMAX_BASE_URL', 'https://api.minimax.io/anthropic')


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
                'tq_contribution': round(tq * 0.65, 2),
                'rec_contribution': round(rec * 0.27, 2),
                'cq_contribution': round(cq * 0.08, 2),
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


def _call_minimax(prompt: str) -> str:
    """Call MiniMax via Anthropic-compatible API (paygo key — not Coding Plan)."""
    if not MINIMAX_API_KEY:
        return 'MiniMax API key not configured. Structured ranking context is available in the response.'

    call_n = register_live_ai_call()
    print(f'AI LIVE prompt #{call_n} (budget {ai_max_display()})')
    try:
        response = requests.post(
            f"{MINIMAX_BASE_URL}/v1/messages",
            headers={
                'x-api-key': MINIMAX_API_KEY,
                'anthropic-version': '2023-06-01',
                'content-type': 'application/json',
            },
            json={
                'model': 'MiniMax-M2.7',
                'max_tokens': 1024,
                'messages': [{'role': 'user', 'content': prompt}],
            },
            timeout=60,
        )
        response.raise_for_status()
        data = response.json()
        content = data.get('content', [])
        if content and isinstance(content, list):
            return content[0].get('text', str(data))
        return str(data)
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
        f"Formula: 65% Team Quality + 27% Record Score + 8% Conference Quality."
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
