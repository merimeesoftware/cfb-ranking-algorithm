
import sys
import os
sys.path.append(os.getcwd())
from main import CFBRankingApp

def check_top_25():
    print("Calculating rankings...")
    app = CFBRankingApp()
    results = app.run_ranking(year=2025, week=None, include_fcs=True)
    teams = results['rankings']['team_rankings']
    
    print(f"\n{'Rank':<5} {'Team':<22} {'FRS':<10} {'Elo':<8} {'Record':<8} {'Conf':<15}")
    print("-" * 75)
    
    for i, team in enumerate(teams[:25]):
        conf_type = team.get('conference_type', '')
        marker = ""
        if conf_type == 'Group of 5':
            marker = " [G5]"
        print(f"{i+1:<5} {team['team_name']:<22} {team['final_ranking_score']:.2f}    {team['team_quality_score']:.0f}     {team['records']['total_wins']}-{team['records']['total_losses']}      {team['conference']}{marker}")

if __name__ == "__main__":
    check_top_25()
