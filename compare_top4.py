import sys
import os
from data_processor import CFBDataProcessor
from ranking_algorithm import TeamQualityRanker

def main():
    year = 2025
    week = 15
    
    print(f"Running comparison for {year} Week {week}...")
    
    processor = CFBDataProcessor(api_key=os.environ.get('CFBD_API_KEY'))
    games = processor.get_games_for_season(year, through_week=week)
    
    ranker = TeamQualityRanker()
    for game in games:
        ranker.update_quality_scores(game)
        
    # Run iterative solver
    for i in range(3):
        print(f"Iteration {i+2}...")
        current_ranks = {t: d['quality_score'] for t, d in ranker.team_stats.items()}
        ranker = TeamQualityRanker() # Reset
        # Re-initialize with priors if needed, but for now just run games
        for game in games:
            ranker.update_quality_scores(game, reference_ranks=current_ranks)
            
    results = ranker.calculate_final_rankings()
    ranker.normalize_scores(results)
    
    teams_to_compare = ['Texas Tech', 'Indiana', 'Georgia', 'Ohio State', 'Oregon']
    
    print(f"{'Team':<15} | {'Rank':<4} | {'FRS':<6} | {'Elo':<6} | {'RecScore':<8} | {'CQ':<6} | {'QW':<2} | {'BL':<2} | {'SoS':<6}")
    print("-" * 80)
    
    rankings = results['team_rankings']
    for i, team in enumerate(rankings):
        name = team['team_name']
        if name in teams_to_compare:
            print(f"{name:<15} | {i+1:<4} | {team['final_ranking_score']:.1f} | {team['team_quality_score']:.1f} | {team['record_score']:.1f} | {team['conference_quality_score']:.1f} | {team['quality_wins']:<2} | {team['bad_losses']:<2} | {team['sos']:.1f}")

if __name__ == "__main__":
    main()
