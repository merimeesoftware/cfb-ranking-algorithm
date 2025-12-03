# filepath: c:\\Users\\micha\\DevProjects\\CFB-Ranking-System\\ranking_algorithm.py
import math
from typing import List, Dict, Any, Optional, TypedDict
from collections import defaultdict

class Record(TypedDict):
    wins: int
    losses: int

class InterConfRecord(TypedDict):
    w: int
    l: int

class InterConfRecords(TypedDict):
    p4: InterConfRecord
    g5: InterConfRecord
    fcs: InterConfRecord

class WinDetail(TypedDict):
    opponent: str
    is_road: bool

class TeamStat(TypedDict):
    quality_score: float
    conference: Optional[str]
    conference_type: str
    games_played: int
    wins: int
    losses: int
    record_vs_p4: Record
    record_vs_g5: Record
    record_vs_fcs: Record
    conf_wins: int
    conf_losses: int
    away_wins: int
    ats_record: Record
    inter_conf_records: InterConfRecords
    wins_details: List[WinDetail]
    schedule: List[str]

class TeamQualityRanker:
    """
    Implements the team quality ranking algorithm (Version 3.9).
    Features:
    - Iterative solver for convergence
    - Asymmetric Elo-like updates
    - Margin of Victory scaling
    - Configurable historical priors (reduced legacy bias)
    - OOC-adjusted conference quality
    - Logarithmic SoS scaling
    - Resume-weighted FRS formula (0.55/0.35/0.10)
    """
    
    def _create_default_team_stat(self) -> TeamStat:
        return {
            'quality_score': 0.0,
            'conference': None,
            'conference_type': 'FCS',
            'games_played': 0,
            'wins': 0,
            'losses': 0,
            'record_vs_p4': {'wins': 0, 'losses': 0},
            'record_vs_g5': {'wins': 0, 'losses': 0},
            'record_vs_fcs': {'wins': 0, 'losses': 0},
            'conf_wins': 0,
            'conf_losses': 0,
            'away_wins': 0,
            'ats_record': {'wins': 0, 'losses': 0},
            'inter_conf_records': {'p4': {'w': 0, 'l': 0}, 'g5': {'w': 0, 'l': 0}, 'fcs': {'w': 0, 'l': 0}},
            'wins_details': [],
            'schedule': []
        }

    def __init__(self, config: Optional[Dict[str, Any]] = None, priors: Optional[Dict[str, float]] = None):
        self.config = config or {}
        self.priors = priors or {}
        
        # Configuration parameters with defaults (Elo Scale)
        self.power_conf_initial = self.config.get('power_conf_initial', 1500.0)
        self.group_five_initial = self.config.get('group5_initial', 1200.0)
        self.fcs_initial = self.config.get('fcs_initial', 900.0)
        
        self.base_factor = self.config.get('base_factor', 40.0) # K-factor
        self.conference_weight = self.config.get('conference_weight', 0.1)
        self.record_weight = self.config.get('record_weight', 0.5)
        
        # V3.9: Configurable prior strength (0.0 = pure tier, 1.0 = full historical)
        # Default 0.3 means 70% tier initial + 30% historical prior
        self.prior_strength = self.config.get('prior_strength', 0.3)
        
        # State
        self.team_stats: Dict[str, TeamStat] = defaultdict(self._create_default_team_stat)
        
        self.weekly_scores = {} # week_num -> {team -> score}
        self.initialized_teams = set()

    @property
    def team_conferences(self) -> Dict[str, str]:
        """Return a mapping of team names to conferences for visualization compatibility."""
        return {team: data['conference'] for team, data in self.team_stats.items() if data['conference']}

    def _initialize_team(self, team_name: str, conference: Optional[str], conference_type: str):
        """Initialize a team with base score if not already seen.
        
        V3.9: Uses configurable prior_strength to blend tier initial with historical prior.
        Formula: initial = (1 - prior_strength) * tier_initial + prior_strength * historical_prior
        """
        if team_name in self.initialized_teams:
            # Update conference info if it was missing (e.g. from FCS game)
            if conference and not self.team_stats[team_name]['conference']:
                self.team_stats[team_name]['conference'] = conference
                self.team_stats[team_name]['conference_type'] = conference_type
            return
        
        # Determine tier-based initial score
        tier_initial = self.fcs_initial
        if conference_type == 'Power 4':
            tier_initial = self.power_conf_initial
        elif conference_type == 'Group of 5':
            tier_initial = self.group_five_initial
        
        # V3.9: Blend tier initial with historical prior based on prior_strength
        # prior_strength=0.3 means 70% tier + 30% prior (reduces legacy bias)
        if team_name in self.priors:
            historical_prior = self.priors[team_name]
            initial_score = (1 - self.prior_strength) * tier_initial + self.prior_strength * historical_prior
        else:
            initial_score = tier_initial
            
        self.team_stats[team_name]['quality_score'] = initial_score
        self.team_stats[team_name]['conference'] = conference
        self.team_stats[team_name]['conference_type'] = conference_type
        self.initialized_teams.add(team_name)

    def update_quality_scores(self, game: Dict[str, Any], reference_ranks: Optional[Dict[str, float]] = None):
        """
        Update team scores based on a single game result using Asymmetric Elo.
        
        Args:
            game: Game data dictionary
            reference_ranks: Optional dictionary of team scores to use for opponent strength.
                           If None, uses current live scores.
        """
        home_team = game['home_team_name']
        away_team = game['away_team_name']
        
        # Initialize teams
        self._initialize_team(home_team, game.get('home_conference'), game.get('home_conference_type', 'FCS'))
        self._initialize_team(away_team, game.get('away_conference'), game.get('away_conference_type', 'FCS'))
        
        home_score = game['home_score']
        away_score = game['away_score']
        
        # Determine outcome
        if home_score > away_score:
            winner, loser = home_team, away_team
            is_home_win = True
        elif away_score > home_score:
            winner, loser = away_team, home_team
            is_home_win = False
        else:
            # Tie - just update games played
            self.team_stats[home_team]['games_played'] += 1
            self.team_stats[away_team]['games_played'] += 1
            return

        # Get opponent strength (S_opp)
        # Use reference ranks if available (from previous iteration), otherwise current
        if reference_ranks:
            s_winner_opp = reference_ranks.get(loser, self.team_stats[loser]['quality_score'])
            s_loser_opp = reference_ranks.get(winner, self.team_stats[winner]['quality_score'])
        else:
            s_winner_opp = self.team_stats[loser]['quality_score']
            s_loser_opp = self.team_stats[winner]['quality_score']

        # Calculate Margin of Victory Multiplier (M_mov)
        score_diff = abs(home_score - away_score)
        m_mov = math.log(score_diff + 1)
        
        # Calculate Tier Asymmetry Multiplier (M_tier)
        # We need to know if this was an "upset" or "expected"
        # Use current scores to determine favorite/underdog status
        q_winner_curr = self.team_stats[winner]['quality_score']
        q_loser_curr = self.team_stats[loser]['quality_score']
        
        winner_conf_type = self.team_stats[winner]['conference_type']
        loser_conf_type = self.team_stats[loser]['conference_type']

        # Calculate Matchup Weight (K-factor scaling based on division)
        # This prevents lower division teams from inflating their scores in closed pools
        matchup_weight = 1.0
        
        if winner_conf_type == 'Power 4' and loser_conf_type == 'Power 4':
            matchup_weight = 1.0
        elif (winner_conf_type == 'Power 4' and loser_conf_type == 'Group of 5') or \
             (winner_conf_type == 'Group of 5' and loser_conf_type == 'Power 4'):
            matchup_weight = 0.8
        elif winner_conf_type == 'Group of 5' and loser_conf_type == 'Group of 5':
            matchup_weight = 0.5 # Dampen G5 movement to prevent them from catching P4 easily
        elif (winner_conf_type in ['Power 4', 'Group of 5'] and loser_conf_type == 'FCS') or \
             (winner_conf_type == 'FCS' and loser_conf_type in ['Power 4', 'Group of 5']):
            matchup_weight = 0.2
        else:
            # FCS vs FCS (or lower) - drastically reduce point exchange
            matchup_weight = 0.1

        # Logistic Elo Calculation
        # Expected score for Winner: E_A = 1 / (1 + 10 ^ ((R_B - R_A) / 400))
        # R_A = Winner Score, R_B = Loser Score
        
        # Use current scores for calculation
        r_winner = self.team_stats[winner]['quality_score']
        r_loser = self.team_stats[loser]['quality_score']
        
        # Calculate expected probability of winner winning
        # If Winner is 1500 and Loser is 1500, E = 0.5
        # If Winner is 2000 and Loser is 1000, E ~ 1.0
        # If Winner is 1000 and Loser is 2000, E ~ 0.0
        
        exponent = (r_loser - r_winner) / 400.0
        expected_score = 1.0 / (1.0 + math.pow(10, exponent))
        
        # Actual score is 1.0 (Win)
        actual_score = 1.0
        
        # Calculate Delta
        # Delta = K * Matchup_Weight * MoV_Multiplier * (Actual - Expected)
        
        delta = self.base_factor * matchup_weight * m_mov * (actual_score - expected_score)
        
        # Apply updates (Zero-Sum)
        self.team_stats[winner]['quality_score'] += delta
        self.team_stats[loser]['quality_score'] -= delta
        
        # Update records
        self.team_stats[winner]['wins'] += 1
        self.team_stats[loser]['losses'] += 1
        self.team_stats[winner]['games_played'] += 1
        self.team_stats[loser]['games_played'] += 1
        
        if is_home_win:
             pass # No specific home/away counter needed for logic, just stats
        else:
             self.team_stats[winner]['away_wins'] += 1
        
        # Update conference records
        if game.get('home_conference') == game.get('away_conference') and game.get('home_conference'):
            self.team_stats[winner]['conf_wins'] += 1
            self.team_stats[loser]['conf_losses'] += 1
        
        # Update vs records
        loser_type = self.team_stats[loser]['conference_type']
        winner_type = self.team_stats[winner]['conference_type']
        
        self._update_vs_record(winner, loser_type, won=True)
        self._update_vs_record(loser, winner_type, won=False)

        # Track win details for Strength of Victory calculation
        # We store the opponent name. We'll look up their final Elo later.
        self.team_stats[winner]['wins_details'].append({
            'opponent': loser,
            'is_road': not is_home_win
        })

        # Update inter-conference records (for Conference Rankings)
        winner_conf = self.team_stats[winner]['conference']
        loser_conf = self.team_stats[loser]['conference']
        
        # Only count if conferences are different AND both have a conference (ignore weird data)
        if winner_conf and loser_conf and winner_conf != loser_conf:
            self._update_inter_conf_record(winner, loser_type, won=True)
            self._update_inter_conf_record(loser, winner_type, won=False)

        # Add to schedule for SoS calculation
        self.team_stats[winner]['schedule'].append(loser)
        self.team_stats[loser]['schedule'].append(winner)

    def _update_vs_record(self, team: str, opponent_type: str, won: bool):
        key_map = {'Power 4': 'p4', 'Group of 5': 'g5', 'FCS': 'fcs'}
        key = key_map.get(opponent_type, 'fcs')
        record_key = f'record_vs_{key}'
        
        if won:
            self.team_stats[team][record_key]['wins'] += 1
        else:
            self.team_stats[team][record_key]['losses'] += 1

    def _update_inter_conf_record(self, team: str, opponent_type: str, won: bool):
        key_map = {'Power 4': 'p4', 'Group of 5': 'g5', 'FCS': 'fcs'}
        key = key_map.get(opponent_type, 'fcs')
        
        if won:
            self.team_stats[team]['inter_conf_records'][key]['w'] += 1
        else:
            self.team_stats[team]['inter_conf_records'][key]['l'] += 1

    def save_weekly_scores(self, week_num: int):
        """Snapshot current scores for the week."""
        snapshot = {team: data['quality_score'] for team, data in self.team_stats.items()}
        self.weekly_scores[week_num] = snapshot

    def calculate_conference_quality(self) -> Dict[str, float]:
        """
        Calculate Conference Quality (CQ) with OOC adjustment.
        CQ = Raw_CQ * OOC_Multiplier
        """
        conf_scores = defaultdict(list)
        
        # 1. Calculate Raw CQ (Avg of top 50% teams)
        for team, data in self.team_stats.items():
            if data['conference'] and data['conference'] != 'FBS Independents':
                conf_scores[data['conference']].append(data['quality_score'])
        
        raw_cq = {}
        for conf, scores in conf_scores.items():
            if not scores:
                raw_cq[conf] = 0
                continue
            # Sort descending
            scores.sort(reverse=True)
            # Take top 50%
            top_n = max(1, len(scores) // 2)
            top_scores = scores[:top_n]
            raw_cq[conf] = sum(top_scores) / len(top_scores)
            
        # 2. Calculate OOC Multiplier
        # New V3.7: Weighted Inter-Conference Performance (P4 vs P4 emphasis)
        
        final_cq = {}
        
        # Group teams by conference
        teams_by_conf = defaultdict(list)
        for team, data in self.team_stats.items():
            if data['conference']:
                teams_by_conf[data['conference']].append(team)

        for conf, raw in raw_cq.items():
            # Aggregate inter-conference records for this conference
            p4_wins = 0
            p4_losses = 0
            g5_wins = 0
            g5_losses = 0
            fcs_wins = 0
            fcs_losses = 0
            
            teams_in_conf = teams_by_conf.get(conf, [])
            for team in teams_in_conf:
                recs = self.team_stats[team]['inter_conf_records']
                p4_wins += recs['p4']['w']
                p4_losses += recs['p4']['l']
                g5_wins += recs['g5']['w']
                g5_losses += recs['g5']['l']
                fcs_wins += recs['fcs']['w']
                fcs_losses += recs['fcs']['l']
            
            # Calculate weighted score
            # Weights: P4=1.0, G5=0.5, FCS=0.1
            # This prioritizes P4 vs P4 performance significantly
            weighted_wins = (p4_wins * 1.0) + (g5_wins * 0.5) + (fcs_wins * 0.1)
            weighted_losses = (p4_losses * 1.0) + (g5_losses * 0.5) + (fcs_losses * 0.1)
            total_weighted_games = weighted_wins + weighted_losses
            
            if total_weighted_games > 0:
                performance_ratio = weighted_wins / total_weighted_games
                # Map ratio (0.0 to 1.0) to multiplier (e.g., 0.8 to 1.2)
                # If ratio is 0.5 (average), multiplier is 1.0
                multiplier = 0.8 + (0.4 * performance_ratio)
            else:
                multiplier = 1.0
                
            final_cq[conf] = raw * multiplier
            
        # Handle FBS Independents
        # Assign them the average quality of Power 4 conferences
        p4_confs = ['SEC', 'Big Ten', 'Big 12', 'ACC']
        p4_scores = [final_cq.get(c, 0) for c in p4_confs if c in final_cq]
        if p4_scores:
            final_cq['FBS Independents'] = sum(p4_scores) / len(p4_scores)
        else:
            final_cq['FBS Independents'] = 1500.0 # Fallback
            
        return final_cq

    def calculate_final_rankings(self) -> Dict[str, Any]:
        """Compute final rankings using FRS formula."""
        
        # Calculate Conference Quality
        conf_quality = self.calculate_conference_quality()
        
        # Calculate final scores
        team_rankings = []
        rankings_dict = {}
        
        for team, data in self.team_stats.items():
            cq = conf_quality.get(data['conference'], 0) if data['conference'] else 0
            
            # Calculate Record Score (0-1000 scale mapped to 1000-2000)
            # New V3.6: Weighted Wins (Road Wins count more)
            
            # Weights
            w_home = 1.0
            w_road = 1.1
            
            # Calculate weighted wins
            # We need to know home vs road wins.
            # team_stats['away_wins'] tracks road wins.
            # team_stats['wins'] tracks total wins.
            # Neutral site games are often counted as away/home in data, but let's assume:
            # Home Wins = Total - Away
            
            total_wins = data['wins']
            away_wins = data['away_wins']
            home_wins = total_wins - away_wins
            
            weighted_wins = (home_wins * w_home) + (away_wins * w_road)
            
            total_games = data['wins'] + data['losses']
            if total_games > 0:
                weighted_win_pct = weighted_wins / total_games
            else:
                weighted_win_pct = 0.0
            
            # Strength of Victory (SoV) - Average Elo of Wins
            # Instead of summing (which double-counts quantity), we take the average quality of wins.
            # This rewards teams for WHO they beat, regardless of how many games they played.
            
            win_elos = []
            for win_info in data['wins_details']:
                opp = win_info['opponent']
                opp_elo = self.team_stats[opp]['quality_score']
                win_elos.append(opp_elo)
            
            sov_bonus = 0.0
            avg_win_elo = 0.0  # Initialize to avoid unbound variable
            if win_elos:
                avg_win_elo = sum(win_elos) / len(win_elos)
                # Bonus: If average win is against > 1200 competition (lowered threshold)
                # Scale: (Avg - 1200) * 0.5 (Increased multiplier)
                # e.g. Avg 1800 (Elite) -> 600 * 0.5 = 300 points.
                # e.g. Avg 1500 (Avg) -> 300 * 0.5 = 150 points.
                # This is a subtle tie-breaker, not a dominant factor.
                if avg_win_elo > 1200:
                    sov_bonus = (avg_win_elo - 1200.0) * 0.5
            
            # Combine into Record Score
            # Base: 1000 + (WeightedWinPct * 1000)
            # Add SoV Bonus
            
            # V3.9: Strength of Schedule (SoS) Component with Logarithmic Scaling
            # Calculate Average Opponent Quality (SoS)
            opponents = data['schedule']
            if opponents:
                opp_elos = [self.team_stats[opp]['quality_score'] for opp in opponents]
                avg_opp_elo = sum(opp_elos) / len(opp_elos)
            else:
                avg_opp_elo = 1500.0 # Default average
            
            # V3.9: Logarithmic SoS scaling for smoother differentiation
            # Rewards tough schedules with diminishing returns to prevent runaway inflation
            # log(max(avg - 1400, 1)) * 150 gives ~0 at 1400, ~150 at 1500, ~270 at 1700, ~330 at 2000
            # This differentiates "tough" from "brutal" schedules without flattening at a cap
            if avg_opp_elo > 1400:
                sos_score = math.log(avg_opp_elo - 1400) * 150
            else:
                # Penalty for very weak schedules (below 1400 avg)
                sos_score = (avg_opp_elo - 1400) * 0.5  # Linear penalty
            
            record_score = 1000.0 + (weighted_win_pct * 1000.0) + sov_bonus + sos_score
            
            # FRS = (W_Team * TQ) + (W_Conf * CQ) + (W_Rec * RS)
            # V3.9 Weights: Team=0.55, Conf=0.1, Record=0.35 (More resume-focused like CFP)
            tq_weight = 0.55
            conf_weight = self.conference_weight
            rec_weight = 0.35
            
            final_score = (tq_weight * data['quality_score']) + \
                          (conf_weight * cq) + \
                          (rec_weight * record_score)
            
            team_entry = {
                'team_name': team,
                'conference': data['conference'],
                'conference_type': data['conference_type'],
                'team_quality_score': data['quality_score'],
                'conference_quality_score': cq,
                'record_score': record_score,
                'final_ranking_score': final_score,
                'sos': avg_opp_elo,
                'sov': avg_win_elo,
                'records': {
                    'total_wins': data['wins'],
                    'total_losses': data['losses'],
                    'conf_wins': data['conf_wins'],
                    'conf_losses': data['conf_losses'],
                    'away_wins': data['away_wins'],
                    'power_wins': data['record_vs_p4']['wins'],
                    'power_losses': data['record_vs_p4']['losses'],
                    'group_five_wins': data['record_vs_g5']['wins'],
                    'group_five_losses': data['record_vs_g5']['losses'],
                    'fcs_wins': data['record_vs_fcs']['wins'],
                    'fcs_losses': data['record_vs_fcs']['losses']
                }
            }
            team_rankings.append(team_entry)
            rankings_dict[team] = team_entry
            
        # Sort teams
        team_rankings.sort(key=lambda x: x['final_ranking_score'], reverse=True)
        
        # Conference rankings
        conf_rankings = []
        # Re-calculate aggregate records for display
        conf_records = defaultdict(lambda: {'p4': {'w':0,'l':0}, 'g5': {'w':0,'l':0}, 'fcs': {'w':0,'l':0}})
        conf_team_counts = defaultdict(int)
        
        for team, data in self.team_stats.items():
            if data['conference']:
                conf_team_counts[data['conference']] += 1
                for k in ['p4', 'g5', 'fcs']:
                    # Use inter_conf_records instead of total records
                    conf_records[data['conference']][k]['w'] += data['inter_conf_records'][k]['w']
                    conf_records[data['conference']][k]['l'] += data['inter_conf_records'][k]['l']

        for conf, avg_q in conf_quality.items():
            recs = conf_records[conf]
            conf_rankings.append({
                'conference_name': conf,
                'average_team_quality': avg_q,
                'number_of_teams': conf_team_counts[conf],
                'record_vs_p4': f"{recs['p4']['w']}-{recs['p4']['l']}",
                'record_vs_g5': f"{recs['g5']['w']}-{recs['g5']['l']}",
                'record_vs_fcs': f"{recs['fcs']['w']}-{recs['fcs']['l']}"
            })
        conf_rankings.sort(key=lambda x: x['average_team_quality'], reverse=True)
        
        return {
            'team_rankings': team_rankings,
            'conference_rankings': conf_rankings,
            'rankings': rankings_dict
        }

    def normalize_scores(self, rankings_data: Dict[str, Any]) -> Dict[str, Any]:
        """Normalize final scores to 0-100 range."""
        teams = rankings_data['team_rankings']
        if not teams:
            return rankings_data
            
        # For Elo, we want to map 1500+ to high scores.
        # Let's find min/max but handle outliers.
        scores = [t['final_ranking_score'] for t in teams]
        min_s = min(scores)
        max_s = max(scores)
        range_s = max_s - min_s if max_s > min_s else 1.0
        
        for team in teams:
            norm = 100 * (team['final_ranking_score'] - min_s) / range_s
            team['normalized_score'] = norm
            # Update the dict version too
            rankings_data['rankings'][team['team_name']]['normalized_score'] = norm
            
        return rankings_data

    @staticmethod
    def calculate_priors(history_data: List[Dict[str, Any]]) -> Dict[str, float]:
        """
        Calculate prior scores based on historical data.
        Expected history_data: List of ranking results (dicts) from previous years,
        ordered from most recent to oldest.
        
        V3.9 Formula: T_prior = 0.67(T_Y-1) + 0.33(T_Y-2)
        - Dropped Y-3 to reduce legacy drag
        - These priors are then blended with tier_initial using prior_strength config
        - Default prior_strength=0.3 means final = 0.7*tier + 0.3*prior
        - Net effect: ~20% Y-1 + ~10% Y-2 influence (down from 50/30/20)
        """
        priors = defaultdict(float)
        weights = [0.67, 0.33]  # V3.9: Only Y-1 and Y-2, dropped Y-3
        
        for i, year_data in enumerate(history_data):
            if i >= len(weights):
                break
            
            weight = weights[i]
            # year_data is the result of calculate_final_rankings()
            # It contains 'rankings' dict mapping team names to data
            rankings = year_data.get('rankings', {})
            
            for team, data in rankings.items():
                # Use final_ranking_score (Elo scale) to maintain consistency
                # Do NOT use normalized_score as it would reset teams to ~50-100 range
                score = data.get('final_ranking_score', 1200.0)
                priors[team] += score * weight
                
        return dict(priors)

# Legacy wrapper for backward compatibility
def calculate_rankings(processed_games, initial_scores, alpha, alpha_away_win_home_loss, k_conf_weight, use_ats_bonus, ats_bonus):
    config = {
        'power_conf_initial': initial_scores.get('Power 4', 100),
        'group5_initial': initial_scores.get('Group of 5', 80),
        'fcs_initial': initial_scores.get('FCS', 60),
        'base_factor': 20.0,
        'conference_weight': k_conf_weight,
        'use_ats': use_ats_bonus,
        'ats_bonus': ats_bonus
    }
    ranker = TeamQualityRanker(config)
    for game in processed_games:
        ranker.update_quality_scores(game)
    return ranker.calculate_final_rankings()

