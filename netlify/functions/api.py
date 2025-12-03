"""
Netlify Serverless Function wrapper for the Flask application.
This wraps the Flask app to work as a Netlify Function.
"""

import sys
import os

# Add the project root to the path so we can import our modules
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from flask import Flask, render_template, request, jsonify
from datetime import datetime
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Import our custom modules
from data_processor import CFBDataProcessor
from ranking_algorithm import TeamQualityRanker

# Create Flask app with correct template and static folders
template_dir = os.path.join(os.path.dirname(__file__), '..', '..', 'templates')
static_dir = os.path.join(os.path.dirname(__file__), '..', '..', 'static')

app = Flask(__name__, template_folder=template_dir, static_folder=static_dir)

# --- Configuration ---
DEFAULT_CONFIG = {
    'power_conf_initial': 1500.0,
    'group5_initial': 1200.0,
    'fcs_initial': 900.0,
    'base_factor': 40.0,
    'conference_weight': 0.10,
    'record_weight': 0.50,
    'prior_strength': 0.30,
    'use_ats': False,
    'ats_bonus': 10.0
}

# Initialize Data Processor
api_key = os.getenv('CFBD_API_KEY')
data_processor = CFBDataProcessor(api_key=api_key) if api_key else None


def get_current_season_week():
    """Determine the current season and week based on today's date."""
    now = datetime.now()
    year = now.year
    
    if now.month < 8:
        return year - 1, None
        
    season_start = datetime(year, 8, 24)
    if now < season_start:
        return year, 1
        
    delta = now - season_start
    week_num = int(delta.days / 7) + 1
    
    if week_num > 16:
        week_num = None
        
    return year, week_num


def calculate_rankings_logic(year, week, request_args):
    """Shared logic to fetch data and calculate rankings."""
    if not data_processor:
        return None
        
    print(f"Fetching games for {year}, week: {week if week else 'all'}...")
    games = data_processor.get_games_for_season(year, through_week=week)
    print(f"Fetched {len(games)} games.")
    
    if not games:
        return None

    games_by_week = data_processor.organize_games_by_week(games)

    history_data = []
    print("Fetching historical data for priors...")
    for h_year in range(year - 1, year - 4, -1):
        try:
            h_games = data_processor.get_games_for_season(h_year)
            if h_games:
                h_config = DEFAULT_CONFIG.copy()
                h_ranker = TeamQualityRanker(h_config) 
                h_games_by_week = data_processor.organize_games_by_week(h_games)
                for w in sorted(h_games_by_week.keys()):
                    for g in h_games_by_week[w]:
                        h_ranker.update_quality_scores(g)
                h_results = h_ranker.calculate_final_rankings()
                h_results = h_ranker.normalize_scores(h_results)
                history_data.append(h_results)
        except Exception as e:
            print(f"Could not process history for {h_year}: {e}")
            continue
            
    priors = TeamQualityRanker.calculate_priors(history_data)
    print(f"Calculated priors for {len(priors)} teams.")

    config = DEFAULT_CONFIG.copy()
    def get_float_arg(key, default):
        val = request_args.get(key)
        return float(val) if val is not None else default

    config['power_conf_initial'] = get_float_arg('power_conf_initial', config['power_conf_initial'])
    config['group5_initial'] = get_float_arg('group5_initial', config['group5_initial'])
    config['fcs_initial'] = get_float_arg('fcs_initial', config['fcs_initial'])
    config['base_factor'] = get_float_arg('base_factor', config['base_factor'])
    config['conference_weight'] = get_float_arg('conference_weight', config['conference_weight'])
    config['record_weight'] = get_float_arg('record_weight', config['record_weight'])
    config['prior_strength'] = get_float_arg('prior_strength', config['prior_strength'])
    
    print("Calculating rankings (Iterative V3.4)...")
    reference_ranks = None
    ranker = TeamQualityRanker(config, priors)
    
    for i in range(3):
        print(f"  Iteration {i+1}/3...")
        ranker = TeamQualityRanker(config, priors)
        for week_num in sorted(games_by_week.keys()):
            for game in games_by_week[week_num]:
                ranker.update_quality_scores(game, reference_ranks)
        if i < 2:
            temp_results = ranker.calculate_final_rankings()
            reference_ranks = {t['team_name']: t['team_quality_score'] for t in temp_results['team_rankings']}
        
    rankings_data = ranker.calculate_final_rankings()
    rankings_data = ranker.normalize_scores(rankings_data)
    
    show_all = request_args.get('all_divisions') == 'true'
    if not show_all:
        fbs_types = ['Power 4', 'Group of 5', 'FBS Independents']
        rankings_data['team_rankings'] = [
            t for t in rankings_data['team_rankings'] 
            if t.get('conference_type') in fbs_types
        ]
        
    return rankings_data


# --- Routes ---

@app.route('/')
def index():
    """Root endpoint."""
    return jsonify({"message": "CFB Ranking API is running", "endpoints": ["/rankings", "/rankings/team/<team_name>"]})


@app.route('/rankings', methods=['GET'])
def get_rankings():
    """API endpoint for fetching rankings JSON."""
    try:
        year = request.args.get('year', default=2023, type=int)
        week = request.args.get('week', default=None, type=int)
        
        data = calculate_rankings_logic(year, week, request.args)
        
        if not data:
            return jsonify({"error": f"No game data found for {year}."}), 404
            
        return jsonify(data)

    except Exception as e:
        print(f"Error during ranking calculation: {e}")
        return jsonify({"error": f"An internal error occurred: {e}"}), 500


@app.route('/rankings/team/<team_name>', methods=['GET'])
def get_team_breakdown(team_name):
    """API endpoint for team ranking breakdown with comparison to nearby teams."""
    try:
        year = request.args.get('year', default=2023, type=int)
        week = request.args.get('week', default=None, type=int)
        
        data = calculate_rankings_logic(year, week, request.args)
        
        if not data:
            return jsonify({"error": f"No game data found for {year}."}), 404
        
        # Find the requested team
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
        
        # Get teams ahead (up to 3)
        teams_ahead = []
        for i in range(max(0, team_index - 3), team_index):
            teams_ahead.append({
                'rank': i + 1,
                **team_rankings[i]
            })
        
        # Get teams behind (up to 3)
        teams_behind = []
        for i in range(team_index + 1, min(len(team_rankings), team_index + 4)):
            teams_behind.append({
                'rank': i + 1,
                **team_rankings[i]
            })
        
        # Build comparison breakdown
        def build_comparison(target, other, target_rank, other_rank):
            """Build a detailed comparison between two teams."""
            diff_final = target['final_ranking_score'] - other['final_ranking_score']
            diff_tq = target['team_quality_score'] - other['team_quality_score']
            diff_rec = target['record_score'] - other['record_score']
            diff_cq = target['conference_quality_score'] - other['conference_quality_score']
            diff_sos = target['sos'] - other['sos']
            diff_sov = target['sov'] - other['sov']
            
            # Determine key factors
            factors = []
            
            # Team Quality contribution (55%)
            tq_contrib = diff_tq * 0.55
            if abs(tq_contrib) > 5:
                factors.append({
                    'factor': 'Team Quality (Elo)',
                    'advantage': 'target' if tq_contrib > 0 else 'other',
                    'diff': abs(diff_tq),
                    'contribution': abs(tq_contrib),
                    'explanation': f"{'Higher' if diff_tq > 0 else 'Lower'} Elo rating ({target['team_quality_score']:.0f} vs {other['team_quality_score']:.0f})"
                })
            
            # Record Score contribution (35%)
            rec_contrib = diff_rec * 0.35
            if abs(rec_contrib) > 5:
                factors.append({
                    'factor': 'Record Score (Resume)',
                    'advantage': 'target' if rec_contrib > 0 else 'other',
                    'diff': abs(diff_rec),
                    'contribution': abs(rec_contrib),
                    'explanation': f"{'Stronger' if diff_rec > 0 else 'Weaker'} resume ({target['record_score']:.0f} vs {other['record_score']:.0f})"
                })
            
            # Conference Quality contribution (10%)
            cq_contrib = diff_cq * 0.10
            if abs(cq_contrib) > 2:
                factors.append({
                    'factor': 'Conference Quality',
                    'advantage': 'target' if cq_contrib > 0 else 'other',
                    'diff': abs(diff_cq),
                    'contribution': abs(cq_contrib),
                    'explanation': f"{'Stronger' if diff_cq > 0 else 'Weaker'} conference ({target['conference']} vs {other['conference']})"
                })
            
            # SoS breakdown
            if abs(diff_sos) > 20:
                factors.append({
                    'factor': 'Strength of Schedule',
                    'advantage': 'target' if diff_sos > 0 else 'other',
                    'diff': abs(diff_sos),
                    'contribution': 0,  # Already included in record score
                    'explanation': f"{'Tougher' if diff_sos > 0 else 'Easier'} schedule (avg opp: {target['sos']:.0f} vs {other['sos']:.0f})"
                })
            
            # SoV breakdown
            if abs(diff_sov) > 20:
                factors.append({
                    'factor': 'Strength of Victory',
                    'advantage': 'target' if diff_sov > 0 else 'other',
                    'diff': abs(diff_sov),
                    'contribution': 0,  # Already included in record score
                    'explanation': f"{'Better' if diff_sov > 0 else 'Weaker'} quality wins (avg win opp: {target['sov']:.0f} vs {other['sov']:.0f})"
                })
            
            # Sort factors by contribution magnitude
            factors.sort(key=lambda x: x['contribution'], reverse=True)
            
            return {
                'other_team': other['team_name'],
                'other_rank': other_rank,
                'other_conference': other['conference'],
                'other_record': f"{other['records']['total_wins']}-{other['records']['total_losses']}",
                'score_diff': diff_final,
                'factors': factors
            }
        
        # Build comparisons
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
        
        # Build response
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
            },
            'formula_breakdown': {
                'tq_contribution': team_data['team_quality_score'] * 0.55,
                'rec_contribution': team_data['record_score'] * 0.35,
                'cq_contribution': team_data['conference_quality_score'] * 0.10,
                'total': team_data['final_ranking_score']
            },
            'comparisons_ahead': comparisons_ahead,
            'comparisons_behind': comparisons_behind
        }
        
        return jsonify(response)

    except Exception as e:
        print(f"Error during team breakdown: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({"error": f"An internal error occurred: {e}"}), 500

# Legacy route for backward compatibility if needed
# @app.route('/rankings_legacy')


# Netlify Functions handler
def handler(event, context):
    """
    Netlify Functions handler.
    Converts AWS Lambda-style events to WSGI requests for Flask.
    """
    from werkzeug.wrappers import Response
    
    # Get request details from the event
    path = event.get('path', '/')
    http_method = event.get('httpMethod', 'GET')
    headers = event.get('headers', {}) or {}
    query_params = event.get('queryStringParameters', {}) or {}
    body = event.get('body', '')
    
    # Strip the /.netlify/functions/api prefix if present
    if path.startswith('/.netlify/functions/api'):
        path = path[len('/.netlify/functions/api'):] or '/'
    
    # Build query string
    query_string = '&'.join(f'{k}={v}' for k, v in query_params.items()) if query_params else ''
    
    # Create a WSGI environment
    environ = {
        'REQUEST_METHOD': http_method,
        'SCRIPT_NAME': '',
        'PATH_INFO': path,
        'QUERY_STRING': query_string,
        'SERVER_NAME': 'netlify',
        'SERVER_PORT': '443',
        'SERVER_PROTOCOL': 'HTTP/1.1',
        'wsgi.version': (1, 0),
        'wsgi.url_scheme': 'https',
        'wsgi.input': __import__('io').BytesIO(body.encode() if body else b''),
        'wsgi.errors': __import__('sys').stderr,
        'wsgi.multithread': False,
        'wsgi.multiprocess': False,
        'wsgi.run_once': True,
    }
    
    # Add headers to environ
    for key, value in headers.items():
        key = key.upper().replace('-', '_')
        if key not in ('CONTENT_TYPE', 'CONTENT_LENGTH'):
            key = f'HTTP_{key}'
        environ[key] = value
    
    # Capture the response
    response_body = []
    response_status = None
    response_headers = []
    
    def start_response(status, headers):
        nonlocal response_status, response_headers
        response_status = status
        response_headers = headers
    
    # Call Flask app
    response_body = app.wsgi_app(environ, start_response)
    
    # Build response
    body_content = b''.join(response_body)
    
    # Parse status code
    status_code = int(response_status.split(' ')[0])
    
    # Build headers dict
    headers_dict = {k: v for k, v in response_headers}
    
    # Check if response is binary
    content_type = headers_dict.get('Content-Type', '')
    is_binary = not content_type.startswith('text/') and not content_type.startswith('application/json')
    
    return {
        'statusCode': status_code,
        'headers': headers_dict,
        'body': body_content.decode('utf-8') if not is_binary else __import__('base64').b64encode(body_content).decode('utf-8'),
        'isBase64Encoded': is_binary
    }
