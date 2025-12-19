
import logging
from main import CFBRankingApp
from ranking_algorithm import TeamQualityRanker

def check_big12():
    app = CFBRankingApp(api_key="dummy")
    rankings = app.run_ranking(2025, None)
    
    print("\n--- Big 12 Elos ---")
    big12_teams = []
    for team in rankings['rankings']['team_rankings']:
        if team['conference'] == 'Big 12':
            big12_teams.append((team['team_name'], team['team_quality_score']))
    
    big12_teams.sort(key=lambda x: x[1], reverse=True)
    for team, elo in big12_teams:
        print(f"{team}: {elo:.2f}")

if __name__ == "__main__":
    logging.basicConfig(level=logging.ERROR)
    check_big12()
