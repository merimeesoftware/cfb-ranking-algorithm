
import math
import statistics
import numpy as np
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
    notes: Optional[str]
    mov: int

class LossDetail(TypedDict):
    opponent: str
    is_home: bool
    notes: Optional[str]
    mov: int

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
    losses_details: List[LossDetail]
    schedule: List[str]

class TeamQualityRanker:
    """
    Implements the team quality ranking algorithm (Version 5).
    Features:
    - Iterative solver (2 passes) for convergence
    - Home-field advantage (HFA=65) with neutral site detection
    - Asymmetric Elo-like updates with upset bonuses (capped at 1.18x)
    - Elo clamping (max 1850) to prevent runaway outliers
    - Margin of Victory scaling (logarithmic)
    - Configurable historical priors (85% fresh, 15% prior)
    - Chaos Tax: conferences with StdDev > 160 get 10% CQ penalty
    - Postseason K-factor reduction (0.65x) to prevent Bowl Bias
    - Synthetic CQ for FBS Independents (schedule-weighted average)
    - Tier-specific SoS/SoV thresholds (P4 vs G5, now equalized)
    - Cross-tier win bonuses for G5 beating P4 (reduced from V4)
    - Explicit loss penalty for multi-loss teams
    - Relative Quality Win Bonus (Top 25%) - uncapped
    - Quality Loss Bonus for losses to Top 20% teams
    - Bad Loss Penalty for losses to Bottom 25% teams
    - Perfection bonus (1.05x undefeated, 1.02x one-loss)
    - Champ Anchors (+100/+50)
    - Resume-weighted FRS formula (0.65/0.27/0.08)
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
            'losses_details': [],
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
        self.conference_weight = self.config.get('conference_weight', 0.08)   # V5.3: 8% CQ
        self.record_weight = self.config.get('record_weight', 0.27)           # V5.3: 27% Resume
        self.team_quality_weight = self.config.get('team_quality_weight', 0.65) # V5.3: 65% TQ
        
        # V4.0: Configurable prior strength (0.0 = pure tier, 1.0 = full historical)
        # Default 0.15 means 85% tier initial + 15% prior (reduced legacy bias)
        self.prior_strength = self.config.get('prior_strength', 0.15)
        
        # V5.3: Number of iterative solver passes (reduced from 4 to 2 for efficiency)
        self.num_iterations = self.config.get('num_iterations', 2)
        
        # V5.3: Home-Field Advantage (HFA) configuration
        self.hfa_elo = self.config.get('hfa_elo', 65.0)  # Standard CFB HFA ~65 Elo points
        self.hfa_postseason = self.config.get('hfa_postseason', 20.0)  # Reduced HFA for bowls
        self.postseason_k_mult = self.config.get('postseason_k_mult', 0.65)  # Bowl K-factor reduction
        
        # V5.3: Elo clamp to prevent runaway outliers
        self.elo_clamp_max = self.config.get('elo_clamp_max', 1850.0)
        
        # V5.3: Chaos Tax configuration (CQ penalty for high-variance conferences)
        self.chaos_stddev_threshold = self.config.get('chaos_stddev_threshold', 160.0)
        self.chaos_tax_multiplier = self.config.get('chaos_tax_multiplier', 0.90)  # 10% penalty
        
        # V4.0+ Loss penalty configuration
        self.loss_penalty_base = self.config.get('loss_penalty_base', 150.0)
        self.loss_penalty_exp = self.config.get('loss_penalty_exp', 1.1) # V4.0+
        
        # V5.3: Upset bonus configuration (dampened from V4)
        self.upset_elo_threshold = self.config.get('upset_elo_threshold', 150.0)  # Elo gap for upset bonus
        self.upset_bonus_mult = self.config.get('upset_bonus_mult', 1.18)  # V5.3: Reduced from 1.25
        self.g5_beats_p4_mult = self.config.get('g5_beats_p4_mult', 1.12)  # V5.3: Reduced from 1.20
        
        # V5.3: Tier-specific SoV thresholds (now equalized)
        self.sov_threshold_p4 = self.config.get('sov_threshold_p4', 1200.0)
        self.sov_threshold_g5 = self.config.get('sov_threshold_g5', 1050.0)
        # V5.3: Equalized multipliers (G5 no longer gets higher SoV mult)
        self.sov_mult_p4 = self.config.get('sov_mult_p4', 0.35)
        self.sov_mult_g5 = self.config.get('sov_mult_g5', 0.35)  # V5.3: Reduced from 0.45 to match P4
        
        # V4.0 Phase 2: Tier-specific SoS baselines
        self.sos_baseline_p4 = self.config.get('sos_baseline_p4', 1420.0)
        self.sos_baseline_g5 = self.config.get('sos_baseline_g5', 1300.0)
        
        # V5.3: Cross-tier win bonus (reduced from V4)
        self.cross_tier_bonus = self.config.get('cross_tier_bonus', 60.0)  # V5.3: Reduced from 80.0
        
        # V4.0 Phase 2: Hybrid CQ weights
        self.cq_top_half_weight = self.config.get('cq_top_half_weight', 0.70)
        self.cq_full_avg_weight = self.config.get('cq_full_avg_weight', 0.30)
        
        # V5.3: Winstreak bonus REMOVED - G5 teams compete on equal footing
        # (previously: winstreak_bonus=150 for G5 teams with ≤1 loss and ≥7 conf wins)
        
        # V5.3: Quality Loss / Bad Loss configuration
        self.quality_loss_mult = self.config.get('quality_loss_mult', 0.10)  # Conservative to avoid V4 imbalance
        self.bad_loss_mult = self.config.get('bad_loss_mult', 0.25)  # Moderate penalty for losing to weak teams
        
        # V5.3: Perfection bonus multipliers
        self.undefeated_mult = self.config.get('undefeated_mult', 1.05)  # 5% bonus for 0-loss 12+ games
        self.one_loss_mult = self.config.get('one_loss_mult', 1.02)  # 2% bonus for 1-loss 12+ games
        
        # State
        self.team_stats: Dict[str, TeamStat] = defaultdict(self._create_default_team_stat)
        
        self.weekly_scores = {} # week_num -> {team -> score}
        self.initialized_teams = set()
        
        # V5.3: Conference StdDevs for chaos tax (populated by previous iteration)
        self.conference_stddevs: Dict[str, float] = {}

    @property
    def team_conferences(self) -> Dict[str, str]:
        """Return a mapping of team names to conferences for visualization compatibility."""
        return {team: data['conference'] for team, data in self.team_stats.items() if data['conference']}

    def _initialize_team(self, team_name: str, conference: Optional[str], conference_type: str):
        """Initialize a team with base score if not already seen.
        
        V4.0: Uses configurable prior_strength to blend tier initial with historical prior.
        Formula: initial = (1 - prior_strength) * tier_initial + prior_strength * historical_prior
        Default prior_strength=0.15 means 85% fresh start + 15% prior (reduces legacy bias).
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
        
        # V4.0: Blend tier initial with historical prior based on prior_strength
        # prior_strength=0.15 means 85% tier + 15% prior (significantly reduces legacy bias)
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
        
        V5.3 Features:
        - Home-Field Advantage (HFA=65) adjusts expected score, not actual ratings
        - Neutral site detection via keyword parsing in game notes
        - Postseason K-factor reduction (0.65x) to prevent Bowl Bias
        - Elo clamping at 1850 to prevent runaway outliers
        
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

        # V5.3: Detect neutral site and postseason games
        game_notes = str(game.get('notes', '')).lower()
        season_type = str(game.get('season_type', 'regular')).lower()
        
        is_neutral_site = 'neutral' in game_notes or 'kickoff' in game_notes
        is_postseason = season_type == 'postseason' or 'bowl' in game_notes or 'playoff' in game_notes or 'championship' in game_notes

        # Calculate Margin of Victory Multiplier (M_mov)
        score_diff = abs(home_score - away_score)
        m_mov = math.log(score_diff + 1)
        
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
            matchup_weight = 0.65  # V4.0: Reduced damping (was 0.5) to allow quality G5 teams to build Elo
        elif (winner_conf_type in ['Power 4', 'Group of 5'] and loser_conf_type == 'FCS') or \
             (winner_conf_type == 'FCS' and loser_conf_type in ['Power 4', 'Group of 5']):
            matchup_weight = 0.2
        else:
            # FCS vs FCS (or lower) - drastically reduce point exchange
            matchup_weight = 0.1

        # Use current TRUE ratings for Elo calculation
        r_home = self.team_stats[home_team]['quality_score']
        r_away = self.team_stats[away_team]['quality_score']
        
        # V5.3: Home-Field Advantage (HFA)
        # Adjust EXPECTED score calculation only, not actual ratings
        # This makes road wins worth more and home wins worth less (as expected)
        if is_neutral_site:
            hfa = 0.0  # No HFA for neutral site games
        elif is_postseason:
            hfa = self.hfa_postseason  # Reduced HFA for bowl games (~20)
        else:
            hfa = self.hfa_elo  # Standard HFA (~65)
        
        # Effective ratings for expectation calculation only
        r_home_effective = r_home + hfa
        r_away_effective = r_away
        
        # Calculate expected score using effective ratings
        # Home team's expected win probability
        exponent = (r_away_effective - r_home_effective) / 400.0
        home_expected = 1.0 / (1.0 + math.pow(10, exponent))
        away_expected = 1.0 - home_expected
        
        # Winner's expected score
        if is_home_win:
            expected_score = home_expected
        else:
            expected_score = away_expected
        
        # Actual score is 1.0 (Win)
        actual_score = 1.0
        
        # V5.3: Postseason K-factor reduction to prevent Bowl Bias
        k_factor = self.base_factor
        if is_postseason:
            k_factor *= self.postseason_k_mult  # 0.65x for bowl games
        
        # Calculate Delta using TRUE ratings (zero-sum on actual strength)
        delta = k_factor * matchup_weight * m_mov * (actual_score - expected_score)
        
        # V5.3: Upset Bonus Multipliers (dampened from V4)
        r_winner = self.team_stats[winner]['quality_score']
        r_loser = self.team_stats[loser]['quality_score']
        elo_gap = r_loser - r_winner
        
        if elo_gap > self.upset_elo_threshold:
            delta *= self.upset_bonus_mult  # Major upset bonus (×1.18)
        
        # G5 beating P4 gets additional bonus (stacks with upset bonus)
        if winner_conf_type == 'Group of 5' and loser_conf_type == 'Power 4':
            delta *= self.g5_beats_p4_mult  # G5 > P4 bonus (×1.12)
        
        # Apply updates (Zero-Sum)
        new_winner_score = self.team_stats[winner]['quality_score'] + delta
        new_loser_score = self.team_stats[loser]['quality_score'] - delta
        
        # V5.3: Elo clamp to prevent runaway outliers
        new_winner_score = min(new_winner_score, self.elo_clamp_max)
        
        self.team_stats[winner]['quality_score'] = new_winner_score
        self.team_stats[loser]['quality_score'] = new_loser_score
        
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
        # V5.0: Include margin of victory (score_diff) for frontend display
        self.team_stats[winner]['wins_details'].append({
            'opponent': loser,
            'is_road': not is_home_win,
            'mov': score_diff,  # Margin of Victory
            'notes': game.get('notes')
        })
        
        # V4.0 Phase 3: Track loss details for Quality Loss Bonus
        # V5.0: Include margin for frontend display
        self.team_stats[loser]['losses_details'].append({
            'opponent': winner,
            'is_home': not is_home_win,  # Loser was home if winner was away
            'mov': score_diff,  # Margin of defeat
            'notes': game.get('notes')
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

    def set_conference_stddevs(self, stddevs: Dict[str, float]):
        """Set conference StdDevs from previous iteration for chaos tax calculation."""
        self.conference_stddevs = stddevs
    
    def compute_conference_stddevs(self) -> Dict[str, float]:
        """Compute StdDev of Elos for each conference (for chaos tax in next iteration)."""
        conf_scores = defaultdict(list)
        for team, data in self.team_stats.items():
            if data['conference'] and data['conference'] != 'FBS Independents':
                conf_scores[data['conference']].append(data['quality_score'])
        
        stddevs = {}
        for conf, scores in conf_scores.items():
            if len(scores) >= 2:
                stddevs[conf] = statistics.stdev(scores)
            else:
                stddevs[conf] = 0.0
        return stddevs

    def calculate_conference_quality(self) -> Dict[str, float]:
        """
        Calculate Conference Quality (CQ) with OOC adjustment and Chaos Tax.
        
        V5.3 Features:
        - Hybrid CQ = 0.7 * top50%_avg + 0.3 * full_avg
        - OOC Multiplier based on inter-conference performance
        - Chaos Tax: 10% penalty for conferences with StdDev > 160
        - Synthetic CQ for FBS Independents (schedule-weighted average)
        """
        conf_scores = defaultdict(list)
        
        # 1. Calculate Raw CQ using Hybrid formula (rewards depth)
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
            # Hybrid CQ - blend top half with full average
            top_n = max(1, len(scores) // 2 + len(scores) % 2)
            top_scores = scores[:top_n]
            top_half_avg = sum(top_scores) / len(top_scores)
            full_avg = sum(scores) / len(scores)
            # Hybrid: 70% top half + 30% full (rewards depth, prevents bottom drag)
            raw_cq[conf] = (self.cq_top_half_weight * top_half_avg) + (self.cq_full_avg_weight * full_avg)
            
        # 2. Calculate OOC Multiplier
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
            weighted_wins = (p4_wins * 1.0) + (g5_wins * 0.5) + (fcs_wins * 0.1)
            weighted_losses = (p4_losses * 1.0) + (g5_losses * 0.5) + (fcs_losses * 0.1)
            total_weighted_games = weighted_wins + weighted_losses
            
            if total_weighted_games > 0:
                performance_ratio = weighted_wins / total_weighted_games
                # Map ratio (0.0 to 1.0) to multiplier (e.g., 0.8 to 1.2)
                multiplier = 0.8 + (0.4 * performance_ratio)
            else:
                multiplier = 1.0
            
            # V5.3: Apply Chaos Tax for high-variance conferences
            # If StdDev > threshold, apply penalty (conferences that cannibalize themselves)
            conf_stddev = self.conference_stddevs.get(conf, 0.0)
            if conf_stddev > self.chaos_stddev_threshold:
                multiplier *= self.chaos_tax_multiplier  # 10% penalty
                
            final_cq[conf] = raw * multiplier
        
        # V5.3: Synthetic CQ for FBS Independents (schedule-weighted average)
        # Instead of CQ=0, use average CQ of opponents' conferences
        # This rewards independents who play tough schedules (Notre Dame vs Army)
        indie_teams = teams_by_conf.get('FBS Independents', [])
        for indie_team in indie_teams:
            schedule = self.team_stats[indie_team]['schedule']
            if schedule:
                opp_cqs = []
                for opp in schedule:
                    opp_conf = self.team_stats[opp]['conference']
                    if opp_conf and opp_conf != 'FBS Independents':
                        opp_cq = final_cq.get(opp_conf, 0)
                        opp_cqs.append(opp_cq)
                if opp_cqs:
                    # Store synthetic CQ for this specific indie team
                    synthetic_cq = sum(opp_cqs) / len(opp_cqs)
                    final_cq[f'_indie_{indie_team}'] = synthetic_cq
        
        # Placeholder for teams without synthetic CQ
        final_cq['FBS Independents'] = 0.0
            
        return final_cq

    def calculate_final_rankings(self) -> Dict[str, Any]:
        """Compute final rankings using FRS formula."""
        
        # Calculate Conference Quality
        conf_quality = self.calculate_conference_quality()
        
        # V4.0+: Calculate Percentiles for Relative QW
        all_elos = [data['quality_score'] for data in self.team_stats.values()]
        if all_elos:
            p75 = np.percentile(all_elos, 75)  # Top 25% threshold for quality wins
            p80 = np.percentile(all_elos, 80)  # Top 20% threshold for quality losses
            p25 = np.percentile(all_elos, 25)  # Bottom 25% threshold for bad losses
        else:
            p75 = 1600.0
            p80 = 1650.0
            p25 = 1100.0

        # Calculate final scores
        team_rankings = []
        rankings_dict = {}
        
        for team, data in self.team_stats.items():
            # V5.3: Use synthetic CQ for independents
            if data['conference'] == 'FBS Independents':
                cq = conf_quality.get(f'_indie_{team}', 0)
            else:
                cq = conf_quality.get(data['conference'], 0) if data['conference'] else 0
            
            # Calculate Record Score (0-1000 scale mapped to 1000-2000)
            # New V3.6: Weighted Wins (Road Wins count more)
            
            # Weights
            w_home = 1.0
            w_road = 1.1
            
            # Calculate weighted wins
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
            win_elos = []
            cross_tier_wins = 0  # V4.0 Phase 2: Count G5 beating P4
            team_conf_type = data['conference_type']
            
            # V4.0+: Champ Anchor Logic
            champ_bonus = 0.0
            is_champ = False
            is_finalist = False

            for win_info in data['wins_details']:
                opp = win_info['opponent']
                opp_elo = self.team_stats[opp]['quality_score']
                opp_conf_type = self.team_stats[opp]['conference_type']
                win_elos.append(opp_elo)
                
                # V4.0 Phase 2: Count cross-tier wins (G5 beating P4)
                if team_conf_type == 'Group of 5' and opp_conf_type == 'Power 4':
                    cross_tier_wins += 1
                
                if 'championship' in str(win_info.get('notes', '')).lower():
                    is_champ = True

            for loss_info in data['losses_details']:
                if 'championship' in str(loss_info.get('notes', '')).lower():
                    is_finalist = True
            
            if is_champ:
                champ_bonus = 100.0
            elif is_finalist:
                champ_bonus = 50.0
            
            sov_bonus = 0.0
            avg_win_elo = 0.0  # Initialize to avoid unbound variable
            if win_elos:
                avg_win_elo = sum(win_elos) / len(win_elos)
                # V4.0 Phase 2: Tier-specific SoV thresholds
                if team_conf_type == 'Power 4':
                    sov_threshold = self.sov_threshold_p4
                    sov_mult = self.sov_mult_p4
                else:  # G5 or other
                    sov_threshold = self.sov_threshold_g5
                    sov_mult = self.sov_mult_g5
                
                if avg_win_elo > sov_threshold:
                    sov_bonus = (avg_win_elo - sov_threshold) * sov_mult
            
            # V4.0 Phase 2: Cross-tier win bonus (+80 per G5 > P4 win)
            cross_tier_bonus = cross_tier_wins * self.cross_tier_bonus
            
            # V3.9: Strength of Schedule (SoS) Component with Logarithmic Scaling
            opponents = data['schedule']
            if opponents:
                opp_elos = [self.team_stats[opp]['quality_score'] for opp in opponents]
                avg_opp_elo = sum(opp_elos) / len(opp_elos)
            else:
                avg_opp_elo = 1500.0 # Default average
            
            # V4.0 Phase 2: Tier-specific SoS baselines
            if team_conf_type == 'Power 4':
                sos_baseline = self.sos_baseline_p4
            else:  # G5 or other
                sos_baseline = self.sos_baseline_g5
            
            # V4.0: Logarithmic SoS scaling for smoother differentiation
            if avg_opp_elo > sos_baseline:
                sos_score = math.log(max(avg_opp_elo - sos_baseline, 1)) * 80
            else:
                # Penalty for weak schedules (below baseline)
                sos_score = (avg_opp_elo - sos_baseline) * 0.5
            
            # V5.3: Relative Quality Win Bonus (UNCAPPED)
            # Bonus for beating Top 25% teams (Elo > P75)
            # Formula: 0.35 * (OppElo - P75) - no cap to reward elite schedules
            qw_bonus = 0.0
            for win_info in data['wins_details']:
                opp = win_info['opponent']
                opp_elo = self.team_stats[opp]['quality_score']
                if opp_elo > p75:
                    bonus = (opp_elo - p75) * 0.35
                    qw_bonus += bonus
            # V5.3: No cap - elite schedules deserve full credit
            
            # V5.3: Quality Loss Bonus - credit for losing to elite teams
            # Conservative multiplier to avoid V4-style imbalance
            quality_loss_bonus = 0.0
            for loss_info in data['losses_details']:
                opp = loss_info['opponent']
                opp_elo = self.team_stats[opp]['quality_score']
                if opp_elo > p80:  # Top 20% teams
                    bonus = (opp_elo - p80) * self.quality_loss_mult
                    quality_loss_bonus += bonus
            
            # V5.3: Bad Loss Penalty - penalize losses to weak teams
            bad_loss_penalty = 0.0
            for loss_info in data['losses_details']:
                opp = loss_info['opponent']
                opp_elo = self.team_stats[opp]['quality_score']
                if opp_elo < p25:  # Bottom 25% teams
                    penalty = (p25 - opp_elo) * self.bad_loss_mult
                    bad_loss_penalty += penalty
            
            # V4.0+: Explicit Loss Penalty - penalizes multi-loss teams progressively
            # Formula: -150 * (losses ^ 1.1)
            num_losses = data['losses']
            loss_penalty = 0.0
            if num_losses > 0:
                loss_penalty = self.loss_penalty_base * (num_losses ** self.loss_penalty_exp)
            
            record_score = 1000.0 + (weighted_win_pct * 1000.0) + sov_bonus + sos_score + cross_tier_bonus + qw_bonus + champ_bonus + quality_loss_bonus - loss_penalty - bad_loss_penalty
            
            # V5.3: Perfection Bonus (multiplicative)
            # Undefeated teams with 12+ games get 5% boost
            # One-loss teams with 12+ games get 2% boost
            games_played = data['wins'] + data['losses']
            if num_losses == 0 and games_played >= 12:
                record_score *= self.undefeated_mult  # 1.05x
            elif num_losses == 1 and games_played >= 12:
                record_score *= self.one_loss_mult  # 1.02x
            
            # FRS = (W_Team * TQ) + (W_Conf * CQ) + (W_Rec * RS)
            tq_weight = self.team_quality_weight
            conf_weight = self.conference_weight
            rec_weight = self.record_weight
            
            final_score = (tq_weight * data['quality_score']) + \
                          (conf_weight * cq) + \
                          (rec_weight * record_score)
            
            # V5.0: Count quality wins and bad losses for frontend display
            quality_wins_count = sum(1 for w in data['wins_details'] 
                                     if self.team_stats[w['opponent']]['quality_score'] > p75)
            bad_losses_count = sum(1 for l in data['losses_details'] 
                                   if self.team_stats[l['opponent']]['quality_score'] < p25)
            quality_losses_count = sum(1 for l in data['losses_details'] 
                                        if self.team_stats[l['opponent']]['quality_score'] > p80)
            
            # V5.0: Enrich wins_details with opponent data for frontend
            # Mark each win as quality win or not based on P75 threshold
            enriched_wins = []
            for win_info in data['wins_details']:
                opp = win_info['opponent']
                opp_elo = self.team_stats[opp]['quality_score']
                enriched_wins.append({
                    'opponent': opp,
                    'opponent_elo': opp_elo,
                    'opponent_rank': 0,  # Will be populated after sorting
                    'is_road': win_info.get('is_road', False),
                    'mov': win_info.get('mov', 0),
                    'notes': win_info.get('notes'),
                    'is_quality_win': bool(opp_elo > p75)  # True quality win marker
                })
            
            # V5.0: Enrich losses_details with opponent data for frontend
            # Mark each loss as quality loss or bad loss based on P80/P25 thresholds
            enriched_losses = []
            for loss_info in data['losses_details']:
                opp = loss_info['opponent']
                opp_elo = self.team_stats[opp]['quality_score']
                enriched_losses.append({
                    'opponent': opp,
                    'opponent_elo': opp_elo,
                    'opponent_rank': 0,  # Will be populated after sorting
                    'is_home': loss_info.get('is_home', False),
                    'mov': loss_info.get('mov', 0),
                    'notes': loss_info.get('notes'),
                    'is_quality_loss': bool(opp_elo > p80),  # Loss to elite team
                    'is_bad_loss': bool(opp_elo < p25)  # Loss to weak team
                })
            
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
                },
                # V5.0: Resume metrics for frontend
                'quality_wins': quality_wins_count,
                'quality_losses': quality_losses_count,
                'bad_losses': bad_losses_count,
                'cross_tier_wins': cross_tier_wins,
                'quality_win_bonus': qw_bonus,
                'quality_loss_bonus': quality_loss_bonus,
                'bad_loss_penalty': bad_loss_penalty,
                'wins_details': enriched_wins,
                'losses_details': enriched_losses
            }
            team_rankings.append(team_entry)
            rankings_dict[team] = team_entry
            
        # Sort teams
        team_rankings.sort(key=lambda x: x['final_ranking_score'], reverse=True)
        
        # V5.0: Populate opponent_rank in wins_details and losses_details
        # Create a rank lookup from sorted team_rankings
        team_rank_lookup = {t['team_name']: rank + 1 for rank, t in enumerate(team_rankings)}
        
        for team_entry in team_rankings:
            for win in team_entry['wins_details']:
                old_rank = win['opponent_rank']
                win['opponent_rank'] = team_rank_lookup.get(win['opponent'], 999)
            for loss in team_entry['losses_details']:
                loss['opponent_rank'] = team_rank_lookup.get(loss['opponent'], 999)
            # Also update the rankings_dict
            rankings_dict[team_entry['team_name']]['wins_details'] = team_entry['wins_details']
            rankings_dict[team_entry['team_name']]['losses_details'] = team_entry['losses_details']
        
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

        # V5.0: Import conference type classifier
        from data_processor import POWER_4_CONFERENCES, GROUP_OF_5_CONFERENCES
        
        def get_conf_type(conf_name: str) -> str:
            if conf_name in POWER_4_CONFERENCES or conf_name == 'FBS Independents':
                return 'Power 4'
            elif conf_name in GROUP_OF_5_CONFERENCES:
                return 'Group of 5'
            else:
                return 'FCS'
        
        for conf, avg_q in conf_quality.items():
            # Skip synthetic indie CQ entries (start with _indie_)
            if conf.startswith('_indie_'):
                continue
            recs = conf_records[conf]
            conf_rankings.append({
                'conference_name': conf,
                'conference_type': get_conf_type(conf),
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
        
        V4.0 Formula: T_prior = 0.70(T_Y-1) + 0.30(T_Y-2)
        - Dropped Y-3 to reduce legacy drag
        - These priors are then blended with tier_initial using prior_strength config
        - Default prior_strength=0.15 means final = 0.85*tier + 0.15*prior
        - Net effect: ~10.5% Y-1 + ~4.5% Y-2 influence (significantly reduced legacy echo)
        """
        priors = defaultdict(float)
        weights = [0.70, 0.30]  # V4.0: 70% Y-1, 30% Y-2 (slight adjustment from 0.67/0.33)
        
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
