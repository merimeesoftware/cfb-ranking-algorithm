
import sys
import json
from data_processor import CFBDataProcessor
from ranking_algorithm import TeamQualityRanker
import numpy as np

def debug_rankings():
    year = 2024
    week = 15
    
    print(f"Fetching data for {year} Week {week}...")
    processor = CFBDataProcessor(api_key="dummy") # Key not needed for cache if available
    games = processor.get_games_for_season(year, through_week=week)
    
    print(f"Processing {len(games)} games...")
    
    # Initialize ranker
    ranker = TeamQualityRanker()
    
    # Run iterations
    for i in range(ranker.num_iterations):
        print(f"Iteration {i+1}...")
        if i > 0:
            stddevs = ranker.compute_conference_stddevs()
            ranker.set_conference_stddevs(stddevs)
            ranker.team_stats.clear()
            ranker.initialized_teams.clear()
            
        for game in games:
            ranker.update_quality_scores(game)
            
    results = ranker.calculate_final_rankings()
    
    # Calculate thresholds manually to verify
    fbs_elos = [
        data['quality_score'] 
        for data in ranker.team_stats.values() 
        if data['conference_type'] in ['Power 4', 'Group of 5']
    ]
    p4_elos = [
        data['quality_score']
        for data in ranker.team_stats.values()
        if data['conference_type'] == 'Power 4'
    ]
    
    p25 = np.percentile(fbs_elos, 25)
    p4_p25 = np.percentile(p4_elos, 25)
    
    print(f"P25 (FBS): {p25:.2f}")
    print(f"P4 P25: {p4_p25:.2f}")
    
    # Find P4 teams with Bad Losses
    print("\nSearching for P4 teams with Bad Losses...")
    found_p4 = False
    for team in results['team_rankings']:
        if team['conference_type'] != 'Power 4':
            continue
            
        if team['bad_losses'] > 0:
            found_p4 = True
            print(f"\nTeam: {team['team_name']} ({team['conference_type']})")
            print(f"Bad Losses: {team['bad_losses']}")
            for loss in team['losses_details']:
                if loss['is_bad_loss']:
                    print(f"  - Lost to {loss['opponent']} (Elo: {loss['opponent_elo']:.2f})")
            
            if found_p4: break # Just show one for now

    if not found_p4:
        print("No P4 bad losses found.")

if __name__ == "__main__":
    debug_rankings()
