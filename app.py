# filepath: c:\Users\micha\DevProjects\CFB-Ranking-System\app.py
import os
from datetime import datetime

from flask import Flask, request, jsonify
from flask_cors import CORS
from dotenv import load_dotenv

from data_processor import CFBDataProcessor
from cache import get_cache
from ranking_service import (
    get_or_calculate_rankings,
    slim_rankings_for_list,
    build_config,
    DEFAULT_CONFIG,
    FRS_WEIGHTS,
)
from agent_service import agent_bp, set_data_processor
from path_to_climb import compute_path_to_climb
from spend_guards import is_cfbd_offline

load_dotenv()

app = Flask(__name__)

# CORS: allow configured origins or wildcard in dev
_cors_origins = os.environ.get('CORS_ORIGINS', '*')
if _cors_origins == '*':
    CORS(app, origins=['*'], supports_credentials=True)
else:
    CORS(app, origins=[o.strip() for o in _cors_origins.split(',')], supports_credentials=True)

cache = get_cache()
api_key = os.getenv('CFBD_API_KEY')
data_processor = CFBDataProcessor(api_key=api_key)
set_data_processor(data_processor)

app.register_blueprint(agent_bp)


def get_current_season_week():
    now = datetime.now()
    year = now.year
    if now.month < 8:
        return year - 1, 15
    season_start = datetime(year, 8, 24)
    # Pre-tip-off August still belongs to the previous completed season
    if now < season_start:
        return year - 1, 15
    delta = now - season_start
    week_num = int(delta.days / 7) + 1
    if week_num > 16:
        week_num = 15
    return year, week_num


@app.route('/')
def index():
    return jsonify({
        "message": "CFB Ranking API is running",
        "endpoints": [
            "/rankings",
            "/rankings/team/<team_name>",
            "/weeks",
            "/cache/stats",
            "/cache/clear",
            "/agent/explain",
            "/agent/blurb",
            "/agent/climb",
            "/agent/health",
        ],
    })


@app.route('/weeks', methods=['GET'])
def get_weeks():
    year = request.args.get('year', default=datetime.now().year, type=int)
    cache_key = cache._generate_key('available_weeks', year)
    cached = cache.get(cache_key)
    if cached is not None:
        weeks = cached
    else:
        weeks = data_processor.get_available_weeks(year)
        # Historical seasons change rarely; current season refreshes hourly
        from cache import TTL_GAMES_HISTORICAL, TTL_GAMES_CURRENT, is_historical_season
        ttl = TTL_GAMES_HISTORICAL if is_historical_season(year) else TTL_GAMES_CURRENT
        cache.set(cache_key, weeks, ttl, prefix='weeks')
    return jsonify({"year": year, "weeks": weeks, "max_week": max(weeks) if weeks else 15})


@app.route('/cache/stats', methods=['GET'])
def cache_stats():
    return jsonify(cache.get_stats())


@app.route('/cache/clear', methods=['POST'])
def clear_cache():
    secret = request.headers.get('X-Cache-Secret') or request.args.get('secret')
    expected_secret = os.environ.get('CACHE_CLEAR_SECRET')
    if not expected_secret:
        return jsonify({"error": "Cache clear disabled; set CACHE_CLEAR_SECRET"}), 403
    if secret != expected_secret:
        return jsonify({"error": "Unauthorized"}), 401
    cache.clear_all()
    return jsonify({"message": "Cache cleared successfully"})


@app.route('/rankings', methods=['GET'])
def get_rankings():
    try:
        year = request.args.get('year', default=2023, type=int)
        week = request.args.get('week', default=None, type=int)
        detail = request.args.get('detail', 'false').lower() == 'true'
        # Detail views need full payloads (skip slim static files)
        data = get_or_calculate_rankings(
            data_processor, year, week, request.args, prefer_static=not detail
        )
        if not data:
            return jsonify({"error": f"No game data found for {year}."}), 404
        if not detail and data.get('detail') is not False:
            data = slim_rankings_for_list(data)
        elif detail and 'rankings' in data:
            # Avoid shipping the duplicate name-keyed map on the wire
            data = {k: v for k, v in data.items() if k != 'rankings'}
        return jsonify(data)
    except Exception as e:
        print(f"Error during ranking calculation: {e}")
        return jsonify({"error": "An internal error occurred during ranking calculation."}), 500


@app.route('/rankings/team/<team_name>', methods=['GET'])
def get_team_breakdown(team_name):
    try:
        year = request.args.get('year', default=2023, type=int)
        week = request.args.get('week', default=None, type=int)
        # Offline: serve static/slim. Online: prefer full payload for wins_details.
        data = get_or_calculate_rankings(
            data_processor,
            year,
            week,
            request.args,
            prefer_static=is_cfbd_offline(),
        )
        if not data:
            return jsonify({"error": f"No game data found for {year}."}), 404

        team_rankings = data.get('team_rankings', [])
        team_index = None
        team_data = None
        for i, team in enumerate(team_rankings):
            if team['team_name'].lower() == team_name.lower():
                team_index = i
                team_data = team
                break
        if team_data is None:
            return jsonify({"error": f"Team '{team_name}' not found in rankings."}), 404

        teams_ahead = [
            {'rank': i + 1, **team_rankings[i]}
            for i in range(max(0, team_index - 3), team_index)
        ]
        teams_behind = [
            {'rank': i + 1, **team_rankings[i]}
            for i in range(team_index + 1, min(len(team_rankings), team_index + 4))
        ]

        def build_comparison(target, other, target_rank, other_rank):
            diff_final = target['final_ranking_score'] - other['final_ranking_score']
            diff_tq = target['team_quality_score'] - other['team_quality_score']
            diff_rec = target['record_score'] - other['record_score']
            diff_cq = target['conference_quality_score'] - other['conference_quality_score']
            diff_sos = target['sos'] - other['sos']
            diff_sov = target['sov'] - other['sov']
            factors = []
            tq_contrib = diff_tq * FRS_WEIGHTS[0]
            if abs(tq_contrib) > 5:
                factors.append({
                    'factor': 'Team Quality (Elo)',
                    'advantage': 'target' if tq_contrib > 0 else 'other',
                    'diff': abs(diff_tq),
                    'contribution': abs(tq_contrib),
                    'explanation': (
                        f"{'Higher' if diff_tq > 0 else 'Lower'} Elo rating "
                        f"({target['team_quality_score']:.0f} vs {other['team_quality_score']:.0f})"
                    ),
                })
            rec_contrib = diff_rec * FRS_WEIGHTS[1]
            if abs(rec_contrib) > 5:
                factors.append({
                    'factor': 'Record Score (Resume)',
                    'advantage': 'target' if rec_contrib > 0 else 'other',
                    'diff': abs(diff_rec),
                    'contribution': abs(rec_contrib),
                    'explanation': (
                        f"{'Stronger' if diff_rec > 0 else 'Weaker'} resume "
                        f"({target['record_score']:.0f} vs {other['record_score']:.0f})"
                    ),
                })
            cq_contrib = diff_cq * FRS_WEIGHTS[2]
            if abs(cq_contrib) > 2:
                factors.append({
                    'factor': 'Conference Quality',
                    'advantage': 'target' if cq_contrib > 0 else 'other',
                    'diff': abs(diff_cq),
                    'contribution': abs(cq_contrib),
                    'explanation': (
                        f"{'Stronger' if diff_cq > 0 else 'Weaker'} conference "
                        f"({target['conference']} vs {other['conference']})"
                    ),
                })
            if abs(diff_sos) > 20:
                factors.append({
                    'factor': 'Strength of Schedule',
                    'advantage': 'target' if diff_sos > 0 else 'other',
                    'diff': abs(diff_sos),
                    'contribution': 0,
                    'explanation': (
                        f"{'Tougher' if diff_sos > 0 else 'Easier'} schedule "
                        f"(avg opp: {target['sos']:.0f} vs {other['sos']:.0f})"
                    ),
                })
            if abs(diff_sov) > 20:
                factors.append({
                    'factor': 'Strength of Victory',
                    'advantage': 'target' if diff_sov > 0 else 'other',
                    'diff': abs(diff_sov),
                    'contribution': 0,
                    'explanation': (
                        f"{'Better' if diff_sov > 0 else 'Weaker'} quality wins "
                        f"(avg win opp: {target['sov']:.0f} vs {other['sov']:.0f})"
                    ),
                })
            factors.sort(key=lambda x: x['contribution'], reverse=True)
            return {
                'other_team': other['team_name'],
                'other_rank': other_rank,
                'other_conference': other['conference'],
                'other_record': f"{other['records']['total_wins']}-{other['records']['total_losses']}",
                'score_diff': diff_final,
                'factors': factors,
            }

        comparisons_ahead = []
        for t in teams_ahead:
            comp = build_comparison(team_data, t, team_index + 1, t['rank'])
            comp['direction'] = 'ahead'
            comparisons_ahead.append(comp)
        comparisons_behind = []
        for t in teams_behind:
            comp = build_comparison(team_data, t, team_index + 1, t['rank'])
            comp['direction'] = 'behind'
            comparisons_behind.append(comp)

        response = {
            'team': {
                'rank': team_index + 1,
                'name': team_data['team_name'],
                'conference': team_data['conference'],
                'record': f"{team_data['records']['total_wins']}-{team_data['records']['total_losses']}",
                'conf_record': f"{team_data['records']['conf_wins']}-{team_data['records']['conf_losses']}",
                'final_score': team_data['final_ranking_score'],
                'team_quality': team_data['team_quality_score'],
                'record_score': team_data['record_score'],
                'conference_quality': team_data['conference_quality_score'],
                'sos': team_data['sos'],
                'sov': team_data['sov'],
                'power_record': f"{team_data['records']['power_wins']}-{team_data['records']['power_losses']}",
                'g5_record': f"{team_data['records']['group_five_wins']}-{team_data['records']['group_five_losses']}",
                'logo': team_data.get('logo'),
                'color': team_data.get('color'),
            },
            'formula_breakdown': {
                'tq_contribution': team_data['team_quality_score'] * FRS_WEIGHTS[0],
                'rec_contribution': team_data['record_score'] * FRS_WEIGHTS[1],
                'cq_contribution': team_data['conference_quality_score'] * FRS_WEIGHTS[2],
                'total': team_data['final_ranking_score'],
            },
            'wins_details': team_data.get('wins_details') or [],
            'losses_details': team_data.get('losses_details') or [],
            'quality_wins': team_data.get('quality_wins'),
            'quality_losses': team_data.get('quality_losses'),
            'bad_losses': team_data.get('bad_losses'),
            'top_10_wins': team_data.get('top_10_wins'),
            'top_25_wins': team_data.get('top_25_wins'),
            'comparisons_ahead': comparisons_ahead,
            'comparisons_behind': comparisons_behind,
            'path_to_climb': compute_path_to_climb(
                team_data,
                team_rankings[team_index - 1] if team_index > 0 else None,
            ),
        }
        return jsonify(response)
    except Exception as e:
        print(f"Error during team breakdown: {e}")
        return jsonify({"error": "An internal error occurred during team breakdown."}), 500


if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5001))
    debug_mode = os.environ.get('FLASK_DEBUG', 'false').lower() == 'true'
    app.run(debug=debug_mode, port=port)
