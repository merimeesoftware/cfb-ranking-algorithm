
import sys
from main import CFBRankingApp
from tabulate import tabulate

def debug_kstate_asu():
    app = CFBRankingApp()
    print("Running rankings for 2025 to compare K-State and ASU...")
    results = app.run_ranking(year=2025, week=None, include_fcs=True)
    
    rankings = results['rankings']['rankings']
    
    t1_name = "Kansas State"
    t2_name = "Arizona State"
    
    t1 = rankings.get(t1_name)
    t2 = rankings.get(t2_name)
    
    if not t1 or not t2:
        print(f"Could not find {t1_name} or {t2_name}")
        return

    print(f"\n--- Comparison: {t1_name} vs {t2_name} ---")
    
    headers = ["Metric", t1_name, t2_name, "Diff"]
    rows = []
    
    rows.append(["Record", f"{t1['records']['total_wins']}-{t1['records']['total_losses']}", f"{t2['records']['total_wins']}-{t2['records']['total_losses']}", ""])
    rows.append(["Final Score", f"{t1['final_ranking_score']:.2f}", f"{t2['final_ranking_score']:.2f}", f"{t1['final_ranking_score'] - t2['final_ranking_score']:.2f}"])
    
    # Components
    rows.append(["Team Quality (Elo)", f"{t1['team_quality_score']:.0f}", f"{t2['team_quality_score']:.0f}", f"{t1['team_quality_score'] - t2['team_quality_score']:.0f}"])
    rows.append(["Record Score", f"{t1['record_score']:.0f}", f"{t2['record_score']:.0f}", f"{t1['record_score'] - t2['record_score']:.0f}"])
    rows.append(["Conf Quality", f"{t1['conference_quality_score']:.0f}", f"{t2['conference_quality_score']:.0f}", f"{t1['conference_quality_score'] - t2['conference_quality_score']:.0f}"])
    
    print(tabulate(rows, headers=headers, tablefmt="grid"))
    
    print("\n--- Record Score Details ---")
    rs_rows = []
    
    # Reconstruct raw points
    # Win Pct
    t1_wp = (t1['records']['total_wins'] + t1['records']['away_wins']*0.1) / (t1['records']['total_wins'] + t1['records']['total_losses'])
    t2_wp = (t2['records']['total_wins'] + t2['records']['away_wins']*0.1) / (t2['records']['total_wins'] + t2['records']['total_losses'])
    rs_rows.append(["Weighted Win % Pts", f"{t1_wp*1000:.0f}", f"{t2_wp*1000:.0f}", f"{(t1_wp-t2_wp)*1000:.0f}"])
    
    rs_rows.append(["Quality Win Bonus", t1['quality_win_bonus'], t2['quality_win_bonus'], t1['quality_win_bonus'] - t2['quality_win_bonus']])
    rs_rows.append(["Quality Wins Count", t1['quality_wins'], t2['quality_wins'], t1['quality_wins'] - t2['quality_wins']])
    rs_rows.append(["Loss Penalty", -t1.get('loss_penalty', 0), -t2.get('loss_penalty', 0), -t1.get('loss_penalty', 0) + t2.get('loss_penalty', 0)])
    rs_rows.append(["SOS", f"{t1['sos']:.0f}", f"{t2['sos']:.0f}", f"{t1['sos'] - t2['sos']:.0f}"])
    
    # Check specific quality wins
    print(tabulate(rs_rows, headers=headers, tablefmt="grid"))
    
    print(f"\n--- {t1_name} Wins ---")
    # We need to access the ranker to get win details if possible, or just infer from what we have
    # The 'rankings' dict doesn't have the full win details list, but the 'ranker' object in results does.
    ranker = results['ranker']
    t1_stats = ranker.team_stats[t1_name]
    
    win_rows = []
    for win in t1_stats['wins_details']:
        opp = win['opponent']
        opp_elo = ranker.team_stats[opp]['quality_score']
        opp_wins = ranker.team_stats[opp]['wins']
        mov = win['mov']
        
        # Check if it triggered QW
        is_qw = False
        bonus = 0
        # Re-implement logic to check
        qw_elo_floor = ranker.qw_elo_floor # 1675
        if opp_elo >= qw_elo_floor:
            is_qw = True
            bonus = 30.0 + (opp_elo - qw_elo_floor) * ranker.qw_mult
        elif opp_elo >= 1500 and opp_wins >= 8:
            is_qw = True
            bonus = 5.0 + ((opp_elo - 1500) * 0.15)
            
        win_rows.append([opp, f"{opp_elo:.0f}", opp_wins, mov, "YES" if is_qw else "No", f"{bonus:.1f}"])
        
    print(tabulate(win_rows, headers=["Opponent", "Elo", "Wins", "MoV", "Is QW?", "Base Bonus"], tablefmt="simple"))

if __name__ == "__main__":
    debug_kstate_asu()
