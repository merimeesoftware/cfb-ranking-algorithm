"""Agent endpoints for ranking explanations and CFBD MCP proxy."""
import os
from functools import wraps
from typing import Any, Dict, Optional

import requests
from flask import Blueprint, jsonify, request

from ranking_service import get_or_calculate_rankings, DEFAULT_CONFIG

agent_bp = Blueprint('agent', __name__, url_prefix='/agent')

_data_processor = None


def set_data_processor(processor) -> None:
    global _data_processor
    _data_processor = processor

CFBD_MCP_URL = os.environ.get('CFBD_MCP_URL', '')
MINIMAX_API_KEY = os.environ.get('MINIMAX_API_KEY', '')
MINIMAX_BASE_URL = os.environ.get('MINIMAX_BASE_URL', 'https://api.minimax.io/anthropic')
AGENT_RATE_LIMIT = int(os.environ.get('AGENT_RATE_LIMIT', '30'))  # requests per hour per IP (stub)


def _require_agent_enabled(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if not MINIMAX_API_KEY and not CFBD_MCP_URL:
            return jsonify({
                'error': 'Agent features disabled. Set MINIMAX_API_KEY or CFBD_MCP_URL.',
            }), 503
        return f(*args, **kwargs)
    return decorated


def _build_team_context(rankings: Dict[str, Any], team_name: str) -> Optional[Dict[str, Any]]:
    for i, team in enumerate(rankings.get('team_rankings', [])):
        if team['team_name'].lower() == team_name.lower():
            return {
                'rank': i + 1,
                'team_name': team['team_name'],
                'conference': team['conference'],
                'final_ranking_score': team['final_ranking_score'],
                'team_quality_score': team['team_quality_score'],
                'record_score': team['record_score'],
                'conference_quality_score': team['conference_quality_score'],
                'records': team.get('records', {}),
                'sos': team.get('sos'),
                'sov': team.get('sov'),
            }
    return None


def _call_minimax(prompt: str) -> str:
    """Call MiniMax via Anthropic-compatible API."""
    if not MINIMAX_API_KEY:
        return 'MiniMax API key not configured. Structured ranking context is available in the response.'

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
    except Exception as e:
        return f'LLM explanation unavailable: {e}'


@agent_bp.route('/health', methods=['GET'])
def agent_health():
    return jsonify({
        'status': 'ok',
        'minimax_configured': bool(MINIMAX_API_KEY),
        'cfbd_mcp_configured': bool(CFBD_MCP_URL),
    })


@agent_bp.route('/explain', methods=['POST'])
@_require_agent_enabled
def explain_ranking():
    """
    Explain why a team is ranked where it is.

    Body: { "team_name": "Georgia", "year": 2024, "week": 10, "question": "optional" }
    """
    from ranking_service import get_or_calculate_rankings, DEFAULT_CONFIG

    if _data_processor is None:
        return jsonify({'error': 'Data processor not initialized'}), 503

    body = request.get_json(silent=True) or {}
    team_name = body.get('team_name') or request.args.get('team_name')
    year = int(body.get('year') or request.args.get('year', 2024))
    week = body.get('week') or request.args.get('week')
    week = int(week) if week is not None else None
    question = body.get('question', f'Why is {team_name} ranked where they are?')

    if not team_name:
        return jsonify({'error': 'team_name is required'}), 400

    rankings = get_or_calculate_rankings(_data_processor, year, week, request.args)
    if not rankings:
        return jsonify({'error': f'No rankings data for {year}'}), 404

    context = _build_team_context(rankings, team_name)
    if not context:
        return jsonify({'error': f"Team '{team_name}' not found in rankings"}), 404

    prompt = (
        f"You are a college football ranking analyst. Answer concisely using ONLY the data provided.\n\n"
        f"Question: {question}\n\n"
        f"Team context (JSON): {context}\n\n"
        f"Formula: 65% Team Quality + 27% Record Score + 8% Conference Quality."
    )
    explanation = _call_minimax(prompt)

    return jsonify({
        'team_name': team_name,
        'year': year,
        'week': week,
        'context': context,
        'explanation': explanation,
        'formula': DEFAULT_CONFIG,
    })


@agent_bp.route('/mcp/query', methods=['POST'])
@_require_agent_enabled
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
