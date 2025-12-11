# filepath: c:\\Users\\micha\\DevProjects\\CFB-Ranking-System\\ranking_algorithm.py
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
    mov: int

class LossDetail(TypedDict):
    opponent: str
    is_home: bool
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
    Implements the team quality ranking algorithm (Version 4.3).
    Features:
    - Iterative solver (3 passes) for convergence
    - Asymmetric Elo-like updates with upset bonuses (capped at 1.3x)
    - Margin of Victory scaling
    - Dynamic historical priors (0.2 * (1 - week/15))
    - Hybrid depth-aware conference quality (70% top half + 30% full)
    - Tier-specific SoS/SoV thresholds (P4 vs G5)
    - Cross-tier win bonuses for G5 beating P4 (capped)
    - Explicit loss penalty for multi-loss teams
    - H2H bonus for top-10/top-25 wins
    - Quality loss bonus for losses to elite teams
    - Resume-weighted FRS formula (0.60/0.25/0.15)
    - Reduced G5 damping (0.65 weight)
    - Normalized Record Score (1500 + Z-score * 200)
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
        self.conference_weight = self.config.get('conference_weight', 0.08) # V4.5: Reduced to 0.08
        self.record_weight = self.config.get('record_weight', 0.42) # V4.5: Increased to 0.42
        
        # V4.3: Dynamic prior strength handled in main.py or passed in config
        self.prior_strength = self.config.get('prior_strength', 0.15)
        
        # V4.3: Number of iterative solver passes (reduced to 3)
        self.num_iterations = self.config.get('num_iterations', 3)
        
        # V4.2/4.6: Contextual Loss/Win Configuration
        self.bl_threshold = self.config.get('bl_threshold', 200.0)  # V4.4: Increased to 200
        self.bl_mult = self.config.get('bl_mult', 0.35)  # V4.6: Increased from 0.15 to 0.35
        self.bl_max_per_loss = self.config.get('bl_max_per_loss', 100.0)  # V4.6: Increased from 75 to 100
        
        # V4.7: Quality Win uses ABSOLUTE threshold (top-15 caliber teams)
        self.qw_elo_floor = self.config.get('qw_elo_floor', 1600.0)  # V4.7: Raised to 1600 for truly elite wins
        self.qw_mult = self.config.get('qw_mult', 0.50)              # Bonus per Elo above floor
        self.qw_max_per_win = self.config.get('qw_max_per_win', 100.0)
        self.qw_max_total = self.config.get('qw_max_total', 400.0)
        
        # V4.4: Bad Win uses ABSOLUTE threshold (truly weak teams only)
        self.bw_elo_ceiling = self.config.get('bw_elo_ceiling', 1300.0)  # Absolute: only weak teams
        self.bw_max_penalty = self.config.get('bw_max_penalty', 40.0)
        
        # V4.3: Conference Quality Adjustments
        self.conf_bl_weight = self.config.get('conf_bl_weight', 0.1)  # V4.3: Increased to 0.1
        self.conf_depth_weight = self.config.get('conf_depth_weight', 20.0)  # V4.3: Weight for depth penalty
        
        # V4.3: Upset bonus configuration
        self.upset_elo_threshold = self.config.get('upset_elo_threshold', 150.0)
        self.upset_bonus_mult = self.config.get('upset_bonus_mult', 1.25)
        self.g5_beats_p4_mult = self.config.get('g5_beats_p4_mult', 1.20)
        self.upset_mult_cap = self.config.get('upset_mult_cap', 1.3) # V4.3: Cap total multiplier
        
        # V4.0 Phase 2: Tier-specific SoV thresholds
        self.sov_threshold_p4 = self.config.get('sov_threshold_p4', 1200.0)
        self.sov_threshold_g5 = self.config.get('sov_threshold_g5', 1050.0)
        # V4.3: Reduced multipliers
        self.sov_mult_p4 = self.config.get('sov_mult_p4', 0.30)   # V4.3: Was 0.35
        self.sov_mult_g5 = self.config.get('sov_mult_g5', 0.40)   # V4.3: Was 0.45
        
        # V4.0 Phase 2: Tier-specific SoS baselines
        self.sos_baseline_p4 = self.config.get('sos_baseline_p4', 1400.0)
        self.sos_baseline_g5 = self.config.get('sos_baseline_g5', 1300.0)
        
        # V4.3: Cross-tier win bonus
        self.cross_tier_bonus = self.config.get('cross_tier_bonus', 40.0)  # V4.3: Reduced to 40
        self.cross_tier_cap = self.config.get('cross_tier_cap', 200.0) # V4.3: Cap total
        
        # V4.0 Phase 2: Hybrid CQ weights
        self.cq_top_half_weight = self.config.get('cq_top_half_weight', 0.70)
        self.cq_full_avg_weight = self.config.get('cq_full_avg_weight', 0.30)
        
        # V4.1: H2H Bonus configuration
        self.h2h_top10_bonus = self.config.get('h2h_top10_bonus', 100.0) # V4.3: Increased to 100
        self.h2h_top25_bonus = self.config.get('h2h_top25_bonus', 50.0)  # V4.3: Increased to 50
        self.h2h_max_bonus = self.config.get('h2h_max_bonus', 250.0)     # V4.3: Increased to 250
        self.h2h_top25_elo_floor = self.config.get('h2h_top25_elo_floor', 1550.0)
        
        # V4.1: Quality Loss Bonus configuration
        self.ql_threshold = self.config.get('ql_threshold', 1600.0)
        self.ql_multiplier = self.config.get('ql_multiplier', 0.165)
        self.ql_max_per_loss = self.config.get('ql_max_per_loss', 33.0)
        
        self.sos_baseline_indie = self.config.get('sos_baseline_indie', 1350.0)
        
        # State
        self.team_stats: Dict[str, TeamStat] = defaultdict(self._create_default_team_stat)
        
        self.weekly_scores = {} # week_num -> {team -> score}
        self.initialized_teams = set()

    @property
    def team_conferences(self) -> Dict[str, str]:
        """Return a mapping of team names to conferences for visualization compatibility."""
        return {team: data['conference'] for team, data in self.team_stats.items() if data['conference']}

    def _initialize_team(self, team_name: str, conference: Optional[str], conference_type: str):
        """Initialize a team with base score if not already seen."""
        if team_name in self.initialized_teams:
            if conference and not self.team_stats[team_name]['conference']:
                self.team_stats[team_name]['conference'] = conference
                self.team_stats[team_name]['conference_type'] = conference_type
            return
        
        tier_initial = self.fcs_initial
        if conference_type == 'Power 4':
            tier_initial = self.power_conf_initial
        elif conference_type == 'Group of 5':
            tier_initial = self.group_five_initial
        
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
        """Update team scores based on a single game result using Asymmetric Elo."""
        home_team = game['home_team_name']
        away_team = game['away_team_name']
        
        self._initialize_team(home_team, game.get('home_conference'), game.get('home_conference_type', 'FCS'))
        self._initialize_team(away_team, game.get('away_conference'), game.get('away_conference_type', 'FCS'))
        
        home_score = game['home_score']
        away_score = game['away_score']
        
        if home_score > away_score:
            winner, loser = home_team, away_team
            is_home_win = True
        elif away_score > home_score:
            winner, loser = away_team, home_team
            is_home_win = False
        else:
            self.team_stats[home_team]['games_played'] += 1
            self.team_stats[away_team]['games_played'] += 1
            return

        if reference_ranks:
            s_winner_opp = reference_ranks.get(loser, self.team_stats[loser]['quality_score'])
            s_loser_opp = reference_ranks.get(winner, self.team_stats[winner]['quality_score'])
        else:
            s_winner_opp = self.team_stats[loser]['quality_score']
            s_loser_opp = self.team_stats[winner]['quality_score']

        score_diff = abs(home_score - away_score)
        m_mov = math.log(score_diff + 1)
        
        winner_conf_type = self.team_stats[winner]['conference_type']
        loser_conf_type = self.team_stats[loser]['conference_type']

        matchup_weight = 1.0
        if winner_conf_type == 'Power 4' and loser_conf_type == 'Power 4':
            matchup_weight = 1.0
        elif (winner_conf_type == 'Power 4' and loser_conf_type == 'Group of 5') or \
             (winner_conf_type == 'Group of 5' and loser_conf_type == 'Power 4'):
            matchup_weight = 0.8
        elif winner_conf_type == 'Group of 5' and loser_conf_type == 'Group of 5':
            matchup_weight = 0.65
        elif (winner_conf_type in ['Power 4', 'Group of 5'] and loser_conf_type == 'FCS') or \
             (winner_conf_type == 'FCS' and loser_conf_type in ['Power 4', 'Group of 5']):
            matchup_weight = 0.2
        else:
            matchup_weight = 0.1

        r_winner = self.team_stats[winner]['quality_score']
        r_loser = self.team_stats[loser]['quality_score']
        
        # V4.7: Aggressive MoV dampening for weak opponents
        # Blowouts against weak teams shouldn't inflate Elo as much
        # Use ABSOLUTE opponent Elo threshold - beating a 1200 Elo team by 60 isn't impressive
        mov_dampening = 1.0
        if r_loser < 1450:  # Weak opponent (absolute threshold)
            # Dampen MoV significantly for weak opponents
            # At 1450 Elo: no dampening
            # At 1250 Elo: 42.5% dampening
            # At 1050 Elo: 85% dampening (max)
            weakness_factor = min((1450 - r_loser) / 400.0, 1.0)
            mov_dampening = 1.0 - (0.85 * weakness_factor)
        
        m_mov *= mov_dampening
        
        exponent = (r_loser - r_winner) / 400.0
        expected_score = 1.0 / (1.0 + math.pow(10, exponent))
        actual_score = 1.0
        
        season_type = game.get('season_type', 'regular')
        notes = str(game.get('notes', '')).lower()
        k_scale = 1.0
        
        if 'playoff' in notes or ('championship' in notes and season_type == 'postseason'):
             k_scale = 0.6
        elif season_type == 'postseason':
             k_scale = 0.7
        elif 'championship' in notes:
             k_scale = 0.7
             
        delta = self.base_factor * k_scale * matchup_weight * m_mov * (actual_score - expected_score)
        
        # V4.3: Upset Bonus Multipliers (Capped)
        upset_mult = 1.0
        elo_gap = r_loser - r_winner
        if elo_gap > self.upset_elo_threshold:
            upset_mult *= self.upset_bonus_mult
        
        if winner_conf_type == 'Group of 5' and loser_conf_type == 'Power 4':
            upset_mult *= self.g5_beats_p4_mult
            
        # Cap total multiplier
        upset_mult = min(upset_mult, self.upset_mult_cap)
        delta *= upset_mult
        
        self.team_stats[winner]['quality_score'] += delta
        self.team_stats[loser]['quality_score'] -= delta
        
        self.team_stats[winner]['wins'] += 1
        self.team_stats[loser]['losses'] += 1
        self.team_stats[winner]['games_played'] += 1
        self.team_stats[loser]['games_played'] += 1
        
        if not is_home_win:
             self.team_stats[winner]['away_wins'] += 1
        
        if game.get('home_conference') == game.get('away_conference') and game.get('home_conference'):
            self.team_stats[winner]['conf_wins'] += 1
            self.team_stats[loser]['conf_losses'] += 1
        
        loser_type = self.team_stats[loser]['conference_type']
        winner_type = self.team_stats[winner]['conference_type']
        
        self._update_vs_record(winner, loser_type, won=True)
        self._update_vs_record(loser, winner_type, won=False)

        self.team_stats[winner]['wins_details'].append({
            'opponent': loser,
            'is_road': not is_home_win,
            'mov': score_diff
        })
        
        self.team_stats[loser]['losses_details'].append({
            'opponent': winner,
            'is_home': not is_home_win,
            'mov': -score_diff
        })

        winner_conf = self.team_stats[winner]['conference']
        loser_conf = self.team_stats[loser]['conference']
        
        if winner_conf and loser_conf and winner_conf != loser_conf:
            self._update_inter_conf_record(winner, loser_type, won=True)
            self._update_inter_conf_record(loser, winner_type, won=False)

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
        snapshot = {team: data['quality_score'] for team, data in self.team_stats.items()}
        self.weekly_scores[week_num] = snapshot

    def _calculate_bad_loss_penalty(self, team_elo: float, losses: List[LossDetail]) -> tuple[float, int]:
        """Calculate penalty for losses to WEAK teams (absolute Elo threshold).
        
        V4.7: Bad Loss = loss to team with Elo < 1550 (objective threshold).
        This is NOT relative to your own Elo - a loss to a 1450 Elo team is bad for everyone.
        1550 Elo roughly corresponds to a .500 P4 team or excellent G5 team.
        """
        if not losses:
            return 0.0, 0
            
        total_penalty = 0.0
        bad_loss_count = 0
        bad_loss_elo_ceiling = self.config.get('bad_loss_elo_ceiling', 1550.0)
        
        for loss in losses:
            opp_name = loss['opponent']
            opp_elo = self.team_stats[opp_name]['quality_score']
            mov = loss.get('mov', -10)
            is_bad = False
            
            # V4.7: Bad Loss = loss to team with Elo < 1550 (ABSOLUTE threshold)
            # Losing to a weak team is bad regardless of your own rating
            if opp_elo < bad_loss_elo_ceiling:
                # Base penalty scales with how weak the opponent is
                elo_below_threshold = bad_loss_elo_ceiling - opp_elo
                base_penalty = 20.0 + (elo_below_threshold * 0.15)
                
                # MoV multiplier - getting blown out by a weak team is worse
                if mov < -14:
                    mov_mult = 1.0 + math.log(abs(mov) - 13) * 0.3
                else:
                    mov_mult = 1.0
                    
                penalty = min(base_penalty * mov_mult, self.bl_max_per_loss)
                total_penalty += penalty
                is_bad = True
            
            if is_bad:
                bad_loss_count += 1
                
        return total_penalty, bad_loss_count

    def _calculate_quality_win_bonus(self, team_elo: float, wins: List[WinDetail]) -> tuple[float, int]:
        """Calculate bonus for beating TOP teams (absolute Elo threshold).
        
        V4.7: Quality Win = Beat a top-15 caliber team (Elo >= 1600).
        Raised from 1550 to ensure only truly elite wins count.
        Bonus scales with opponent strength and margin of victory.
        """
        total_bonus = 0.0
        quality_win_count = 0
        
        for win in wins:
            opp_name = win['opponent']
            opp_elo = self.team_stats[opp_name]['quality_score']
            opp_wins = self.team_stats[opp_name]['wins']
            mov = win.get('mov', 10)
            
            # Quality Win: Beat a TOP team (absolute threshold)
            # 1600+ Elo = roughly top 25 caliber
            # OR 1500+ Elo AND 9+ Wins (Reward beating good record teams like Houston)
            is_quality = False
            base_bonus = 0.0
            
            if opp_elo >= self.qw_elo_floor:
                elo_above_floor = opp_elo - self.qw_elo_floor
                base_bonus = 20.0 + (elo_above_floor * self.qw_mult)
                is_quality = True
            elif opp_elo >= 1500 and opp_wins >= 8:
                # Special case for good record but lower Elo
                base_bonus = 15.0 + ((opp_elo - 1500) * 0.2)
                is_quality = True
                
            if is_quality:
                # MoV multiplier: bonus for dominant wins over top teams
                mov_mult = 1.0
                if mov >= 14:
                    mov_mult = 1.0 + math.log(mov - 12) * 0.15  # Up to ~1.4x for blowouts
                elif mov >= 7:
                    mov_mult = 1.0  # Solid win
                else:
                    mov_mult = 0.8  # Close game - still quality but less impressive
                
                bonus = min(base_bonus * mov_mult, self.qw_max_per_win)
                total_bonus += bonus
                quality_win_count += 1
                
        return min(total_bonus, self.qw_max_total), quality_win_count

    def _calculate_bad_win_penalty(self, team_elo: float, wins: List[WinDetail]) -> tuple[float, int]:
        """Calculate penalty for struggling against WEAK teams (absolute Elo threshold).
        
        Bad Win = Close win (7 pts or less) against a truly weak team (Elo < 1300).
        This is an absolute threshold - we don't punish good teams for beating average teams.
        """
        total_penalty = 0.0
        bad_win_count = 0
        
        for win in wins:
            opp_name = win['opponent']
            opp_elo = self.team_stats[opp_name]['quality_score']
            mov = win['mov']
            
            # Bad win: Close win (7 pts or less) against a WEAK team (absolute threshold)
            # 1300 Elo = bottom tier FBS / weak G5 teams
            if opp_elo < self.bw_elo_ceiling and mov <= 7:
                penalty = 10.0 + (7 - mov) * 1.5
                total_penalty += min(penalty, self.bw_max_penalty)
                bad_win_count += 1
                
        return total_penalty, bad_win_count

    def calculate_conference_quality(self, bad_loss_map: Optional[Dict[str, float]] = None) -> Dict[str, float]:
        conf_scores = defaultdict(list)
        conf_bl_totals = defaultdict(list)
        
        for team, data in self.team_stats.items():
            if data['conference'] and data['conference'] != 'FBS Independents':
                conf_scores[data['conference']].append(data['quality_score'])
                if bad_loss_map:
                    conf_bl_totals[data['conference']].append(bad_loss_map.get(team, 0.0))
        
        raw_cq = {}
        for conf, scores in conf_scores.items():
            if not scores:
                raw_cq[conf] = 0
                continue
            scores.sort(reverse=True)
            top_n = max(1, len(scores) // 2 + len(scores) % 2)
            top_scores = scores[:top_n]
            top_half_avg = sum(top_scores) / len(top_scores)
            full_avg = sum(scores) / len(scores)
            base_cq = (self.cq_top_half_weight * top_half_avg) + (self.cq_full_avg_weight * full_avg)
            
            if len(scores) > 1:
                std_dev = statistics.stdev(scores)
            else:
                std_dev = 0.0
            
            # V4.3: Depth Penalty for high variance
            # adj = - (std_dev / 200) * 20 (max -20)
            depth_adj = - (std_dev / 200.0) * self.conf_depth_weight
            depth_adj = max(depth_adj, -self.conf_depth_weight)
            
            bl_penalty = 0.0
            if conf in conf_bl_totals and conf_bl_totals[conf]:
                avg_bl = sum(conf_bl_totals[conf]) / len(conf_bl_totals[conf])
                bl_penalty = avg_bl * self.conf_bl_weight
            
            raw_cq[conf] = base_cq + depth_adj - bl_penalty
            
        final_cq = {}
        teams_by_conf = defaultdict(list)
        for team, data in self.team_stats.items():
            if data['conference']:
                teams_by_conf[data['conference']].append(team)

        for conf, raw in raw_cq.items():
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
            
            weighted_wins = (p4_wins * 1.2) + (g5_wins * 0.5) + (fcs_wins * 0.1)
            weighted_losses = (p4_losses * 1.2) + (g5_losses * 0.5) + (fcs_losses * 0.1)
            total_weighted_games = weighted_wins + weighted_losses
            
            if total_weighted_games > 0:
                performance_ratio = weighted_wins / total_weighted_games
                multiplier = 0.8 + (0.4 * performance_ratio)
                # V4.3: Cap OOC multiplier
                multiplier = max(0.9, min(multiplier, 1.1))
            else:
                multiplier = 1.0
                
            final_cq[conf] = raw * multiplier
            
        p4_cqs = [cq for conf, cq in final_cq.items() if conf in ['SEC', 'Big Ten', 'ACC', 'Big 12', 'Pac-12']]
        if p4_cqs:
            final_cq['FBS Independents'] = sum(p4_cqs) / len(p4_cqs)
        else:
            final_cq['FBS Independents'] = 0.0
            
        return final_cq

    def calculate_final_rankings(self) -> Dict[str, Any]:
        bad_loss_map = {}
        quality_win_map = {}
        bad_win_map = {}
        
        bad_loss_counts = {}
        quality_win_counts = {}
        bad_win_counts = {}
        
        for team, data in self.team_stats.items():
            team_elo = data['quality_score']
            
            bl_penalty, bl_count = self._calculate_bad_loss_penalty(team_elo, data['losses_details'])
            bad_loss_map[team] = bl_penalty
            bad_loss_counts[team] = bl_count
            
            qw_bonus, qw_count = self._calculate_quality_win_bonus(team_elo, data['wins_details'])
            quality_win_map[team] = qw_bonus
            quality_win_counts[team] = qw_count
            
            bw_penalty, bw_count = self._calculate_bad_win_penalty(team_elo, data['wins_details'])
            bad_win_map[team] = bw_penalty
            bad_win_counts[team] = bw_count
        
        conf_quality = self.calculate_conference_quality(bad_loss_map)
        
        team_rankings = []
        rankings_dict = {}
        indie_cqs = []
        
        # First pass: Calculate raw record scores for normalization
        raw_record_scores = {}
        
        for team, data in self.team_stats.items():
            if data['conference'] == 'FBS Independents':
                opp_cqs = []
                opp_elos = []
                for opp in data['schedule']:
                    opp_conf = self.team_stats[opp]['conference']
                    if opp_conf:
                        opp_cqs.append(conf_quality.get(opp_conf, 0))
                    opp_elos.append(self.team_stats[opp]['quality_score'])
                
                if opp_cqs:
                    avg_sched_cq = sum(opp_cqs) / len(opp_cqs)
                    avg_opp_elo = sum(opp_elos) / len(opp_elos) if opp_elos else 1500
                    # V4.3: Indie CQ = 0.6 * sched + 0.4 * opp_elo
                    cq = (0.6 * avg_sched_cq) + (0.4 * avg_opp_elo)
                else:
                    cq = conf_quality.get('FBS Independents', 0)
                indie_cqs.append(cq)
            else:
                cq = conf_quality.get(data['conference'], 0) if data['conference'] else 0
            
            w_home = 1.0
            w_road = 1.1
            
            total_wins = data['wins']
            away_wins = data['away_wins']
            home_wins = total_wins - away_wins
            
            weighted_wins = (home_wins * w_home) + (away_wins * w_road)
            
            total_games = data['wins'] + data['losses']
            if total_games > 0:
                weighted_win_pct = weighted_wins / total_games
            else:
                weighted_win_pct = 0.0
            
            win_elos = []
            cross_tier_wins = 0
            team_conf_type = data['conference_type']
            
            for win_info in data['wins_details']:
                opp = win_info['opponent']
                opp_elo = self.team_stats[opp]['quality_score']
                opp_conf_type = self.team_stats[opp]['conference_type']
                win_elos.append(opp_elo)
                
                if team_conf_type == 'Group of 5' and opp_conf_type == 'Power 4':
                    cross_tier_wins += 1
            
            sov_bonus = 0.0
            avg_win_elo = 0.0
            if win_elos:
                avg_win_elo = sum(win_elos) / len(win_elos)
                if team_conf_type == 'Power 4':
                    sov_threshold = self.sov_threshold_p4
                    sov_mult = self.sov_mult_p4
                else:
                    sov_threshold = self.sov_threshold_g5
                    sov_mult = self.sov_mult_g5
                
                if avg_win_elo > sov_threshold:
                    sov_bonus = (avg_win_elo - sov_threshold) * sov_mult
            
            # V4.3: Cap Cross Tier Bonus
            cross_tier_bonus = min(cross_tier_wins * self.cross_tier_bonus, self.cross_tier_cap)
            
            opponents = data['schedule']
            if opponents:
                opp_elos = [self.team_stats[opp]['quality_score'] for opp in opponents]
                avg_opp_elo = sum(opp_elos) / len(opp_elos)
            else:
                avg_opp_elo = 1500.0
            
            if team_conf_type == 'Power 4':
                sos_baseline = self.sos_baseline_p4
            else:
                sos_baseline = self.sos_baseline_g5
            
            if avg_opp_elo > sos_baseline:
                sos_score = math.log(max(avg_opp_elo - sos_baseline, 1)) * 80
            else:
                sos_score = (avg_opp_elo - sos_baseline) * 0.5
            
            h2h_bonus = 0.0
            top10_wins = 0
            top25_wins = 0
            for win_info in data['wins_details']:
                opp = win_info['opponent']
                opp_elo = self.team_stats[opp]['quality_score']
                if opp_elo > 1650:
                    top10_wins += 1
                elif opp_elo > self.h2h_top25_elo_floor:
                    top25_wins += 1
            h2h_bonus = (top10_wins * self.h2h_top10_bonus) + (top25_wins * self.h2h_top25_bonus)
            h2h_bonus = min(h2h_bonus, self.h2h_max_bonus)
            
            ql_bonus = 0.0
            quality_loss_count = 0
            num_losses = data['losses']
            if num_losses > 0 and data['losses_details']:
                quality_loss_points = 0.0
                for loss_info in data['losses_details']:
                    opp = loss_info['opponent']
                    opp_elo = self.team_stats[opp]['quality_score']
                    if opp_elo > self.ql_threshold:
                        loss_credit = (opp_elo - self.ql_threshold) * self.ql_multiplier
                        loss_credit = min(loss_credit, self.ql_max_per_loss)
                        quality_loss_points += loss_credit
                        quality_loss_count += 1
                ql_bonus = quality_loss_points / num_losses
            
            bl_penalty = bad_loss_map.get(team, 0.0)
            qw_bonus = quality_win_map.get(team, 0.0)
            bw_penalty = bad_win_map.get(team, 0.0)
            
            # Raw Record Score Calculation
            raw_score = 1000.0 + (weighted_win_pct * 1000.0) + sov_bonus + sos_score + cross_tier_bonus + h2h_bonus + ql_bonus + qw_bonus - bl_penalty - bw_penalty
            
            raw_record_scores[team] = {
                'raw_score': raw_score,
                'components': {
                    'weighted_win_pct': weighted_win_pct,
                    'sov_bonus': sov_bonus,
                    'sos_score': sos_score,
                    'cross_tier_bonus': cross_tier_bonus,
                    'h2h_bonus': h2h_bonus,
                    'ql_bonus': ql_bonus,
                    'qw_bonus': qw_bonus,
                    'bl_penalty': bl_penalty,
                    'bw_penalty': bw_penalty,
                    'avg_opp_elo': avg_opp_elo,
                    'avg_win_elo': avg_win_elo,
                    'cq': cq,
                    'top10_wins': top10_wins,
                    'top25_wins': top25_wins,
                    'cross_tier_wins': cross_tier_wins,
                    'quality_loss_count': quality_loss_count
                }
            }

        # V4.3: Normalize Record Scores
        # Record = 1500 + zscore(raw) * 200
        all_raw_scores = [d['raw_score'] for d in raw_record_scores.values()]
        if all_raw_scores:
            mean_raw = statistics.mean(all_raw_scores)
            stdev_raw = statistics.stdev(all_raw_scores) if len(all_raw_scores) > 1 else 1.0
        else:
            mean_raw = 0
            stdev_raw = 1
            
        for team, data in raw_record_scores.items():
            raw = data['raw_score']
            comps = data['components']
            
            # Z-score normalization
            z_score = (raw - mean_raw) / stdev_raw if stdev_raw > 0 else 0
            record_score = 1500.0 + (z_score * 200.0)
            
            tq_weight = self.config.get('team_quality_weight', 0.50)
            conf_weight = self.conference_weight
            rec_weight = self.record_weight
            
            final_score = (tq_weight * self.team_stats[team]['quality_score']) + \
                          (conf_weight * comps['cq']) + \
                          (rec_weight * record_score)
            
            # V4.3: Damping for multi-loss P4 teams
            # if num_losses > 2 and tier == 'P4': frs *= 0.95
            if self.team_stats[team]['losses'] > 2 and self.team_stats[team]['conference_type'] == 'Power 4':
                final_score *= 0.95
            
            team_entry = {
                'team_name': team,
                'conference': self.team_stats[team]['conference'],
                'conference_type': self.team_stats[team]['conference_type'],
                'team_quality_score': self.team_stats[team]['quality_score'],
                'conference_quality_score': comps['cq'],
                'record_score': record_score,
                'final_ranking_score': final_score,
                'sos': comps['avg_opp_elo'],
                'sov': comps['avg_win_elo'],
                'records': {
                    'total_wins': self.team_stats[team]['wins'],
                    'total_losses': self.team_stats[team]['losses'],
                    'conf_wins': self.team_stats[team]['conf_wins'],
                    'conf_losses': self.team_stats[team]['conf_losses'],
                    'away_wins': self.team_stats[team]['away_wins'],
                    'power_wins': self.team_stats[team]['record_vs_p4']['wins'],
                    'power_losses': self.team_stats[team]['record_vs_p4']['losses'],
                    'group_five_wins': self.team_stats[team]['record_vs_g5']['wins'],
                    'group_five_losses': self.team_stats[team]['record_vs_g5']['losses'],
                    'fcs_wins': self.team_stats[team]['record_vs_fcs']['wins'],
                    'fcs_losses': self.team_stats[team]['record_vs_fcs']['losses']
                },
                'quality_losses': comps['quality_loss_count'],
                'quality_wins': quality_win_counts.get(team, 0),
                'bad_losses': bad_loss_counts.get(team, 0),
                'bad_wins': bad_win_counts.get(team, 0),
                'top_10_wins': comps['top10_wins'],
                'top_25_wins': comps['top25_wins'],
                'cross_tier_wins': comps['cross_tier_wins'],
                'h2h_bonus': comps['h2h_bonus'],
                'quality_loss_bonus': comps['ql_bonus'],
                'bad_loss_penalty': comps['bl_penalty'],
                'quality_win_bonus': comps['qw_bonus'],
                'bad_win_penalty': comps['bw_penalty']
            }
            team_rankings.append(team_entry)
            rankings_dict[team] = team_entry
        
        if indie_cqs:
            conf_quality['FBS Independents'] = sum(indie_cqs) / len(indie_cqs)
            
        team_rankings.sort(key=lambda x: x['final_ranking_score'], reverse=True)
        
        conf_rankings = []
        conf_records = defaultdict(lambda: {'p4': {'w':0,'l':0}, 'g5': {'w':0,'l':0}, 'fcs': {'w':0,'l':0}})
        conf_team_counts = defaultdict(int)
        conf_types = {}
        
        for team, data in self.team_stats.items():
            if data['conference']:
                conf_team_counts[data['conference']] += 1
                if data['conference'] not in conf_types:
                    conf_types[data['conference']] = data['conference_type']
                for k in ['p4', 'g5', 'fcs']:
                    conf_records[data['conference']][k]['w'] += data['inter_conf_records'][k]['w']
                    conf_records[data['conference']][k]['l'] += data['inter_conf_records'][k]['l']

        for conf, avg_q in conf_quality.items():
            recs = conf_records[conf]
            conf_rankings.append({
                'conference_name': conf,
                'conference_type': conf_types.get(conf, 'FCS'),
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
            
        scores = [t['final_ranking_score'] for t in teams]
        min_s = min(scores)
        max_s = max(scores)
        range_s = max_s - min_s if max_s > min_s else 1.0
        
        for team in teams:
            norm = 100 * (team['final_ranking_score'] - min_s) / range_s
            team['normalized_score'] = norm
            rankings_data['rankings'][team['team_name']]['normalized_score'] = norm
            
        return rankings_data

    @staticmethod
    def calculate_priors(history_data: List[Dict[str, Any]]) -> Dict[str, float]:
        priors = defaultdict(float)
        weights = [0.70, 0.30]
        
        for i, year_data in enumerate(history_data):
            if i >= len(weights):
                break
            
            weight = weights[i]
            rankings = year_data.get('rankings', {})
            
            for team, data in rankings.items():
                score = data.get('final_ranking_score', 1200.0)
                priors[team] += score * weight
                
        return dict(priors)

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

