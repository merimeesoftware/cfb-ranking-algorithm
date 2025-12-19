
import logging
from main import CFBRankingApp

def check_g5():
    app = CFBRankingApp(api_key="dummy")
    rankings = app.run_ranking(2024, None)
    
    print("\n--- Top G5 Teams ---")
    g5_teams = []
    for team in rankings['rankings']['team_rankings']:
        if team['conference_type'] == 'Group of 5':
            g5_teams.append(team)
    
    g5_teams.sort(key=lambda x: x['final_ranking_score'], reverse=True)
    for i, team in enumerate(g5_teams[:10]):
        print(f"#{i+1} {team['team_name']} ({team['conference']}): {team['final_ranking_score']:.2f}")

if __name__ == "__main__":
    logging.basicConfig(level=logging.ERROR)
    check_g5()
