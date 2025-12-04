# filepath: c:\Users\micha\DevProjects\CFB-Ranking-System\app.py
import os
from datetime import datetime
from flask import Flask, request, jsonify
from flask_cors import CORS
from dotenv import load_dotenv
from data_processor import CFBDataProcessor
from ranking_algorithm import TeamQualityRanker

# Load environment variables (especially CFBD_API_KEY)
load_dotenv()

app = Flask(__name__)

# Enable CORS for all routes - allows frontend to call API from different domain
CORS(app, origins=["*"], supports_credentials=True)

# --- Configuration ---
# Default parameters
DEFAULT_CONFIG = {
    'power_conf_initial': 1500.0,
    'group5_initial': 1200.0,
    'fcs_initial': 900.0,
    'base_factor': 40.0,
    'conference_weight': 0.10,
    'record_weight': 0.50,
    'prior_strength': 0.30,  # V3.9: 30% historical, 70% fresh
    'use_ats': False,
    'ats_bonus': 10.0
}

# Initialize Data Processor
# We initialize it once. If API key rotates, this might need to be inside request, 
# but for standard app it's fine here.
api_key = os.getenv('CFBD_API_KEY')
data_processor = CFBDataProcessor(api_key=api_key)

def get_current_season_week():
    """Determine the current season and week based on today's date."""
    now = datetime.now()
    year = now.year
    
    # CFB season typically starts late August / early September
    # If we are in Jan-July, we are likely in the 'offseason' of the previous year's season
    # or just before the new season.
    # Let's assume if month < 8, we default to previous year final.
    if now.month < 8:
        return year - 1, None # None means 'All' / Postseason
        
    # If we are in season (Aug-Dec), we need to estimate the week.
    # Week 1 is usually around Labor Day (first Monday of Sept).
    # This is a rough heuristic. For precise week, we'd need to query the API.
    # But for default UI values, a heuristic or API call is fine.
    
    # Let's try to use the data_processor to get the current week if possible,
    # or just default to a safe bet.
    # Since we want to be "smart", let's just return the year and let the frontend
    # or the user select the week, OR default to 'All' which is safe.
    # The user specifically asked for "current year and current week".
    
    # Simple heuristic for week number:
    # Week 1 starts approx Sept 1st.
    # Each week is 7 days.
    # Calculate weeks since Sept 1.
    
    season_start = datetime(year, 8, 24) # Approx Week 0 start
    if now < season_start:
        return year, 1
        
    delta = now - season_start
    week_num = int(delta.days / 7) + 1
    
    # Cap at 15/16
    if week_num > 16:
        week_num = None # Postseason / All
        
    return year, week_num

def calculate_rankings_logic(year, week, request_args):
    """Shared logic to fetch data and calculate rankings."""
    # --- Fetch Data ---
    print(f"Fetching games for {year}, week: {week if week else 'all'}...")
    games = data_processor.get_games_for_season(year, through_week=week)
    print(f"Fetched {len(games)} games.")
    
    if not games:
        return None

    # Organize games by week
    games_by_week = data_processor.organize_games_by_week(games)

    # --- Calculate Priors ---
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

    # --- Configure Ranker ---
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
    
    # --- Calculate Rankings ---
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
    
    # Filter Results
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

# --- Main Execution ---
if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5001))
    debug_mode = os.environ.get('FLASK_DEBUG', 'false').lower() == 'true'
    app.run(debug=debug_mode, port=port)
