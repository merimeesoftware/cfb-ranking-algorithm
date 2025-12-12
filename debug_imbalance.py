
import sys
from main import CFBRankingApp
from tabulate import tabulate

def debug_imbalance():
    app = CFBRankingApp()
    # Run for 2025 (since that's what the user's output showed)
    print("Running rankings for 2025...")
    results = app.run_ranking(year=2025, week=None, include_fcs=True)
    
    rankings = results['rankings']['rankings']
    
    teams_of_interest = ["Indiana", "Texas Tech"]
    
    print("\n--- Detailed Component Analysis ---")
    
    headers = ["Component", "Indiana", "Texas Tech", "Diff (Ind - TT)"]
    rows = []
    
    ind = rankings.get("Indiana")
    tt = rankings.get("Texas Tech")
    
    if not ind or not tt:
        print("Teams not found.")
        return

    # 1. Final Scores
    rows.append(["Final Ranking Score", f"{ind['final_ranking_score']:.2f}", f"{tt['final_ranking_score']:.2f}", f"{ind['final_ranking_score'] - tt['final_ranking_score']:.2f}"])
    rows.append(["Normalized Score", f"{ind.get('normalized_score', 0):.2f}", f"{tt.get('normalized_score', 0):.2f}", f"{ind.get('normalized_score', 0) - tt.get('normalized_score', 0):.2f}"])
    
    # 2. Weighted Components
    # FRS = 0.55*TQ + 0.37*RS + 0.08*CQ
    tq_w = 0.55
    rs_w = 0.37
    cq_w = 0.08
    
    ind_tq_contrib = ind['team_quality_score'] * tq_w
    tt_tq_contrib = tt['team_quality_score'] * tq_w
    rows.append(["Team Quality (Weighted 55%)", f"{ind_tq_contrib:.2f} (Raw: {ind['team_quality_score']:.0f})", f"{tt_tq_contrib:.2f} (Raw: {tt['team_quality_score']:.0f})", f"{ind_tq_contrib - tt_tq_contrib:.2f}"])
    
    ind_rs_contrib = ind['record_score'] * rs_w
    tt_rs_contrib = tt['record_score'] * rs_w
    rows.append(["Record Score (Weighted 37%)", f"{ind_rs_contrib:.2f} (Raw: {ind['record_score']:.0f})", f"{tt_rs_contrib:.2f} (Raw: {tt['record_score']:.0f})", f"{ind_rs_contrib - tt_rs_contrib:.2f}"])
    
    ind_cq_contrib = ind['conference_quality_score'] * cq_w
    tt_cq_contrib = tt['conference_quality_score'] * cq_w
    rows.append(["Conf Quality (Weighted 8%)", f"{ind_cq_contrib:.2f} (Raw: {ind['conference_quality_score']:.0f})", f"{tt_cq_contrib:.2f} (Raw: {tt['conference_quality_score']:.0f})", f"{ind_cq_contrib - tt_cq_contrib:.2f}"])
    
    print(tabulate(rows, headers=headers, tablefmt="grid"))
    
    print("\n--- Record Score Breakdown (Raw Points) ---")
    # We need to access the raw components which are not fully in the final output dict
    # But we can infer some or look at the 'records' and bonus fields
    
    rs_rows = []
    rs_headers = ["Item", "Indiana", "Texas Tech", "Diff"]
    
    # Reconstruct approximate raw score components
    # Base = 1000
    # WinPct
    ind_wp = (ind['records']['total_wins'] + ind['records']['away_wins']*0.1) / (ind['records']['total_wins'] + ind['records']['total_losses'])
    tt_wp = (tt['records']['total_wins'] + tt['records']['away_wins']*0.1) / (tt['records']['total_wins'] + tt['records']['total_losses'])
    rs_rows.append(["Weighted Win % Pts", f"{ind_wp*1000:.0f}", f"{tt_wp*1000:.0f}", f"{(ind_wp-tt_wp)*1000:.0f}"])
    
    # Bonuses
    rs_rows.append(["H2H Bonus", ind['h2h_bonus'], tt['h2h_bonus'], ind['h2h_bonus'] - tt['h2h_bonus']])
    rs_rows.append(["Quality Win Bonus", ind['quality_win_bonus'], tt['quality_win_bonus'], ind['quality_win_bonus'] - tt['quality_win_bonus']])
    rs_rows.append(["Quality Loss Bonus", ind['quality_loss_bonus'], tt['quality_loss_bonus'], ind['quality_loss_bonus'] - tt['quality_loss_bonus']])
    rs_rows.append(["Bad Loss Penalty", -ind['bad_loss_penalty'], -tt['bad_loss_penalty'], -ind['bad_loss_penalty'] + tt['bad_loss_penalty']])
    rs_rows.append(["Bad Win Penalty", -ind['bad_win_penalty'], -tt['bad_win_penalty'], -ind['bad_win_penalty'] + tt['bad_win_penalty']])
    rs_rows.append(["Loss Penalty", -ind.get('loss_penalty', 0), -tt.get('loss_penalty', 0), -ind.get('loss_penalty', 0) + tt.get('loss_penalty', 0)])
    rs_rows.append(["Undefeated Bonus", ind.get('undefeated_bonus', 0), tt.get('undefeated_bonus', 0), ind.get('undefeated_bonus', 0) - tt.get('undefeated_bonus', 0)])
    
    # SOS/SOV (Approximate points)
    # SOS Score: log(max(AvgOpp - Baseline, 1)) * 80
    # P4 Baseline 1400
    ind_sos_pts = 0
    if ind['sos'] > 1400:
        import math
        ind_sos_pts = math.log(ind['sos'] - 1400) * 80
    
    tt_sos_pts = 0
    if tt['sos'] > 1400:
        import math
        tt_sos_pts = math.log(tt['sos'] - 1400) * 80
        
    rs_rows.append(["SOS Score (Approx)", f"{ind_sos_pts:.0f} (SOS {ind['sos']:.0f})", f"{tt_sos_pts:.0f} (SOS {tt['sos']:.0f})", f"{ind_sos_pts - tt_sos_pts:.0f}"])
    
    print(tabulate(rs_rows, headers=rs_headers, tablefmt="grid"))
    
    print("\n--- Conference Analysis ---")
    conf_rankings = results['rankings']['conference_rankings']
    b12 = next(c for c in conf_rankings if c['conference_name'] == 'Big 12')
    b10 = next(c for c in conf_rankings if c['conference_name'] == 'Big Ten')
    
    c_rows = []
    c_rows.append(["Avg Team Quality", b10['average_team_quality'], b12['average_team_quality']])
    c_rows.append(["Record vs P5", b10['record_vs_p4'], b12['record_vs_p4']])
    c_rows.append(["Record vs G5", b10['record_vs_g5'], b12['record_vs_g5']])
    
    print(tabulate(c_rows, headers=["Metric", "Big Ten", "Big 12"], tablefmt="grid"))

if __name__ == "__main__":
    debug_imbalance()
