from data_processor import CFBDataProcessor
from ranking_algorithm import TeamQualityRanker

def main():
    p = CFBDataProcessor()
    games = p.get_games_for_season(2025, 15)
    ranker = TeamQualityRanker()
    for g in games:
        ranker.update_quality_scores(g)
        
    # Run iterations
    for _ in range(3):
        current_ranks = {t: d['quality_score'] for t, d in ranker.team_stats.items()}
        ranker = TeamQualityRanker()
        for g in games:
            ranker.update_quality_scores(g, reference_ranks=current_ranks)

    for team_name in ['Ohio State', 'Texas Tech']:
        print(f"\n{team_name} Wins Analysis:")
        data = ranker.team_stats[team_name]
        wins = data['wins_details']
        for w in wins:
            opp = w['opponent']
            opp_data = ranker.team_stats[opp]
            elo = opp_data['quality_score']
            wins_count = opp_data['wins']
            
            is_qw = False
            if elo >= 1600:
                is_qw = True
            elif elo >= 1500 and wins_count >= 8:
                is_qw = True
                
            print(f"  vs {opp:<15} | Elo: {elo:.1f} | Wins: {wins_count} | QW: {is_qw}")

if __name__ == "__main__":
    main()
