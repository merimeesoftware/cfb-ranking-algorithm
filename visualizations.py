#!/usr/bin/env python3
# visualizations.py
"""
Visualization utilities for the CFB Ranking System.
Creates tables and charts for displaying ranking results.
"""

from typing import Dict, List, Optional, Any, Tuple, Union, cast
import logging
import matplotlib.pyplot as plt
import matplotlib as mpl
import matplotlib.patches as mpatches
import seaborn as sns
import pandas as pd
from tabulate import tabulate
import numpy as np

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class RankingVisualizer:
    """
    Provides visualization tools for the CFB ranking system.
    """
    
    def __init__(self, style: str = 'default'):
        """
        Initialize the visualizer with a style.
        
        Args:
            style: Matplotlib/seaborn style name
        """
        # Set up visualization style
        if style != 'default':
            plt.style.use(style)
        
        # Use seaborn for better looking plots
        sns.set_style("whitegrid")
        
        # Default color scheme
        self.conference_colors = {
            'SEC': '#FF4136',       # Red
            'Big Ten': '#0074D9',   # Blue
            'ACC': '#FF851B',       # Orange
            'Big 12': '#FFDC00',    # Yellow
            'Pac-12': '#3D9970',    # Green
            'American Athletic': '#B10DC9',  # Purple
            'Conference USA': '#2ECC40',     # Green
            'Mid-American': '#F012BE',       # Magenta
            'Mountain West': '#7FDBFF',      # Light blue
            'Sun Belt': '#01FF70',           # Green
            'FCS': '#AAAAAA',       # Gray for FCS conferences
        }
        
        # Set default figure size
        plt.rcParams['figure.figsize'] = (12, 8)
        
    def create_rankings_table(self, rankings: Dict[str, Dict], 
                             include_records: bool = True,
                             top_n: Optional[int] = None) -> str:
        """
        Create a formatted table of rankings.
        
        Args:
            rankings: Dictionary of team rankings
            include_records: Whether to include record details
            top_n: If provided, only include top N teams
            
        Returns:
            Formatted table as string
        """
        # Sort teams by final ranking score (descending)
        sorted_teams = sorted(
            rankings.values(), 
            key=lambda x: x['final_ranking_score'], 
            reverse=True
        )
        
        # Limit to top N if specified
        if top_n:
            sorted_teams = sorted_teams[:top_n]
        
        # Create table data
        table_data = []
        for i, team_data in enumerate(sorted_teams, 1):
            team = team_data['team_name']
            conference = team_data['conference']
            quality_score = team_data['team_quality_score']
            conf_quality = team_data['conference_quality_score']
            final_score = team_data['final_ranking_score']
            normalized = team_data.get('normalized_score', 0)
            
            # Format record data
            if include_records and 'records' in team_data:
                records = team_data['records']
                record = f"{records['total_wins']}-{records['total_losses']}"
                conf_record = f"{records['conf_wins']}-{records['conf_losses']}"
                vs_p5 = f"{records['power_wins']}-{records['power_losses']}"
                vs_g5 = f"{records['group_five_wins']}-{records['group_five_losses']}"
                vs_fcs = f"{records['fcs_wins']}-{records['fcs_losses']}"
                
                row = [
                    i, team, conference, record, conf_record,
                    vs_p5, vs_g5, vs_fcs, 
                    f"{quality_score:.2f}", f"{conf_quality:.2f}", f"{final_score:.2f}"
                ]
            else:
                row = [
                    i, team, conference, 
                    f"{quality_score:.2f}", f"{conf_quality:.2f}", f"{final_score:.2f}"
                ]
                
            table_data.append(row)
        
        # Create headers
        if include_records:
            headers = [
                "Rank", "Team", "Conference", "Record", "Conf Record",
                "vs P5", "vs G5", "vs FCS", 
                "Team Quality", "Conf Quality", "Final Score"
            ]
        else:
            headers = [
                "Rank", "Team", "Conference",
                "Team Quality", "Conf Quality", "Final Score"
            ]
        
        # Generate table
        return tabulate(table_data, headers=headers, tablefmt="fancy_grid")
    
    def create_conference_table(self, rankings: Dict[str, Dict]) -> str:
        """
        Create a table of conference rankings.
        
        Args:
            rankings: Dictionary of team rankings
            
        Returns:
            Formatted table as string
        """
        # Calculate conference data
        conf_data = {}
        for team_data in rankings.values():
            conf = team_data['conference']
            if conf not in conf_data:
                conf_data[conf] = {
                    'team_count': 0,
                    'total_wins': 0,
                    'total_losses': 0,
                    'p5_wins': 0,
                    'p5_losses': 0,
                    'g5_wins': 0,
                    'g5_losses': 0,
                    'fcs_wins': 0,
                    'fcs_losses': 0,
                    'quality_score': team_data['conference_quality_score'],
                    'teams': []
                }
            
            # Increment counters
            conf_data[conf]['team_count'] += 1
            conf_data[conf]['teams'].append(team_data['team_name'])
            
            # Add records if available
            if 'records' in team_data:
                records = team_data['records']
                conf_data[conf]['total_wins'] += records['total_wins']
                conf_data[conf]['total_losses'] += records['total_losses']
                conf_data[conf]['p5_wins'] += records['power_wins']
                conf_data[conf]['p5_losses'] += records['power_losses']
                conf_data[conf]['g5_wins'] += records['group_five_wins']
                conf_data[conf]['g5_losses'] += records['group_five_losses']
                conf_data[conf]['fcs_wins'] += records['fcs_wins']
                conf_data[conf]['fcs_losses'] += records['fcs_losses']
        
        # Sort conferences by quality score (descending)
        sorted_confs = sorted(
            [(conf, data) for conf, data in conf_data.items()],
            key=lambda x: x[1]['quality_score'],
            reverse=True
        )
        
        # Create table data
        table_data = []
        for i, (conf, data) in enumerate(sorted_confs, 1):
            quality_score = data['quality_score']
            team_count = data['team_count']
            total_record = f"{data['total_wins']}-{data['total_losses']}"
            vs_p5 = f"{data['p5_wins']}-{data['p5_losses']}"
            vs_g5 = f"{data['g5_wins']}-{data['g5_losses']}"
            vs_fcs = f"{data['fcs_wins']}-{data['fcs_losses']}"
            
            # Get win percentages
            p5_win_pct = data['p5_wins'] / max(1, data['p5_wins'] + data['p5_losses'])
            g5_win_pct = data['g5_wins'] / max(1, data['g5_wins'] + data['g5_losses'])
            fcs_win_pct = data['fcs_wins'] / max(1, data['fcs_wins'] + data['fcs_losses'])
            
            row = [
                i, conf, team_count, total_record,
                vs_p5, f"{p5_win_pct:.3f}",
                vs_g5, f"{g5_win_pct:.3f}",
                vs_fcs, f"{fcs_win_pct:.3f}",
                f"{quality_score:.2f}"
            ]
            table_data.append(row)
        
        # Create headers
        headers = [
            "Rank", "Conference", "Teams", "Total Record",
            "vs P5", "P5 Win%", 
            "vs G5", "G5 Win%", 
            "vs FCS", "FCS Win%",
            "Quality Score"
        ]
        
        # Generate table
        return tabulate(table_data, headers=headers, tablefmt="fancy_grid")
    
    def plot_team_rankings(self, rankings: Dict[str, Dict], 
                          top_n: int = 25,
                          save_path: Optional[str] = None):
        """
        Create a bar chart of the top N teams by final ranking score.
        
        Args:
            rankings: Dictionary of team rankings
            top_n: Number of teams to include
            save_path: If provided, save the plot to this path
        """
        # Sort teams by final ranking score (descending)
        sorted_teams = sorted(
            rankings.values(), 
            key=lambda x: x['final_ranking_score'], 
            reverse=True
        )
        
        # Limit to top N
        sorted_teams = sorted_teams[:top_n]
        
        # Create data
        teams = [t['team_name'] for t in sorted_teams]
        scores = [t['final_ranking_score'] for t in sorted_teams]
        conferences = [t['conference'] for t in sorted_teams]
        
        # Create color mapping
        colors = [self.conference_colors.get(conf, '#333333') for conf in conferences]
        
        # Create figure
        fig, ax = plt.subplots(figsize=(14, 10))
        
        # Create bar chart
        bars = ax.barh(teams[::-1], scores[::-1], color=colors[::-1])
        
        # Add labels
        ax.set_title(f'Top {top_n} Teams by Ranking Score', fontsize=16)
        ax.set_xlabel('Final Ranking Score', fontsize=12)
        
        # Add conference legend
        conf_set = set(conferences)
        handles = [mpatches.Rectangle((0,0), 1, 1, color=self.conference_colors.get(conf, '#333333')) 
                 for conf in conf_set]
        ax.legend(handles, conf_set, loc='lower right')
        
        # Add score labels
        for i, bar in enumerate(bars):
            width = bar.get_width()
            ax.text(width + 2, bar.get_y() + bar.get_height()/2, 
                    f'{width:.1f}', ha='left', va='center')
        
        plt.tight_layout()
        
        # Save or show
        if save_path:
            plt.savefig(save_path, dpi=300, bbox_inches='tight')
            logger.info(f"Saved plot to {save_path}")
        else:
            plt.show()
    
    def plot_conference_rankings(self, rankings: Dict[str, Dict],
                                save_path: Optional[str] = None):
        """
        Create a bar chart of conferences by quality score.
        
        Args:
            rankings: Dictionary of team rankings
            save_path: If provided, save the plot to this path
        """
        # Calculate conference data
        conf_data = {}
        for team_data in rankings.values():
            conf = team_data['conference']
            if conf is None:
                conf = "Unknown"
                
            if conf not in conf_data:
                conf_data[conf] = {
                    'quality_score': team_data['conference_quality_score'],
                    'team_count': 0
                }
            conf_data[conf]['team_count'] += 1
        
        # Sort conferences by quality score (descending)
        sorted_confs = sorted(
            [(conf, data) for conf, data in conf_data.items() if data['team_count'] >= 3],
            key=lambda x: x[1]['quality_score'],
            reverse=True
        )
        
        # Create data
        confs = [c[0] for c in sorted_confs]
        scores = [c[1]['quality_score'] for c in sorted_confs]
        team_counts = [c[1]['team_count'] for c in sorted_confs]
        
        # Create color mapping
        colors = [self.conference_colors.get(conf, '#333333') for conf in confs]
        
        # Create figure
        fig, ax = plt.subplots(figsize=(12, 8))
        
        # Create bar chart
        bars = ax.bar(confs, scores, color=colors)
        
        # Add labels
        ax.set_title('Conference Quality Scores', fontsize=16)
        ax.set_ylabel('Conference Quality Score', fontsize=12)
        ax.tick_params(axis='x', rotation=45)
        
        # Add team count labels
        for i, bar in enumerate(bars):
            height = bar.get_height()
            ax.text(bar.get_x() + bar.get_width()/2., height + 1,
                   f'{team_counts[i]} teams', ha='center', va='bottom')
        
        # Add score labels
        for i, bar in enumerate(bars):
            height = bar.get_height()
            ax.text(bar.get_x() + bar.get_width()/2., height/2,
                   f'{height:.1f}', ha='center', va='center', color='white', fontweight='bold')
        
        plt.tight_layout()
        
        # Save or show
        if save_path:
            plt.savefig(save_path, dpi=300, bbox_inches='tight')
            logger.info(f"Saved plot to {save_path}")
        else:
            plt.show()
    
    def plot_quality_progression(self, ranker, 
                                teams: Optional[List[str]] = None,
                                save_path: Optional[str] = None):
        """
        Plot the progression of team quality scores over weeks.
        
        Args:
            ranker: TeamQualityRanker instance with weekly_scores data
            teams: List of teams to include (defaults to top 10)
            save_path: If provided, save the plot to this path
        """
        if not ranker.weekly_scores:
            logger.warning("No weekly scores data available")
            return
            
        # If no teams provided, use top 10 from final week
        if teams is None:
            final_week = max(ranker.weekly_scores.keys())
            final_scores = ranker.weekly_scores[final_week]
            teams = sorted(final_scores.keys(), 
                          key=lambda t: final_scores[t], 
                          reverse=True)[:10]
        
        # Create data for plot
        weeks = sorted(ranker.weekly_scores.keys())
        
        plt.figure(figsize=(14, 8))
        
        # Plot each team's progression
        for team in teams:
            scores = []
            for week in weeks:
                if team in ranker.weekly_scores[week]:
                    scores.append(ranker.weekly_scores[week][team])
                else:
                    # If team doesn't have a score for this week, use previous week's score
                    prev_score = scores[-1] if scores else 0
                    scores.append(prev_score)
            
            # Get conference for color
            conference = ranker.team_conferences.get(team, 'Unknown')
            color = self.conference_colors.get(conference, '#333333')
            
            plt.plot(weeks, scores, marker='o', label=team, linewidth=2, color=color)
        
        plt.title("Team Quality Score Progression by Week", fontsize=16)
        plt.xlabel("Week", fontsize=12)
        plt.ylabel("Team Quality Score", fontsize=12)
        plt.xticks(weeks)
        plt.grid(True, linestyle='--', alpha=0.7)
        plt.legend(loc='upper left', bbox_to_anchor=(1, 1))
        
        plt.tight_layout()
        
        # Save or show
        if save_path:
            plt.savefig(save_path, dpi=300, bbox_inches='tight')
            logger.info(f"Saved plot to {save_path}")
        else:
            plt.show()
    
    def create_team_matchup_chart(self, team1: str, team2: str, rankings: Dict[str, Dict],
                                save_path: Optional[str] = None):
        """
        Create a comparison chart for two teams.
        
        Args:
            team1: First team name
            team2: Second team name
            rankings: Dictionary of team rankings
            save_path: If provided, save the plot to this path
        """
        if team1 not in rankings or team2 not in rankings:
            logger.error(f"One or both teams not found in rankings")
            return
            
        team1_data = rankings[team1]
        team2_data = rankings[team2]
        
        # Create data for radar chart
        categories = ['Team Quality', 'Conf Quality', 'P5 Wins', 'G5 Wins', 'Away Wins']
        
        team1_values = [
            team1_data['team_quality_score'],
            team1_data['conference_quality_score'],
            team1_data['records']['power_wins'],
            team1_data['records']['group_five_wins'],
            team1_data['records']['away_wins']
        ]
        
        team2_values = [
            team2_data['team_quality_score'],
            team2_data['conference_quality_score'],
            team2_data['records']['power_wins'],
            team2_data['records']['group_five_wins'],
            team2_data['records']['away_wins']
        ]
        
        # Normalize data for radar chart
        max_vals = [max(t1, t2) for t1, t2 in zip(team1_values, team2_values)]
        max_vals = [max(1, val) for val in max_vals]  # Avoid division by zero
        
        team1_norm = [val / max_val for val, max_val in zip(team1_values, max_vals)]
        team2_norm = [val / max_val for val, max_val in zip(team2_values, max_vals)]
        
        # Create radar chart
        angles = np.linspace(0, 2*np.pi, len(categories), endpoint=False).tolist()
        angles += angles[:1]  # Close the loop
        
        team1_norm += team1_norm[:1]  # Close the loop
        team2_norm += team2_norm[:1]  # Close the loop
        
        categories += categories[:1]  # Close the loop
        
        fig, ax = plt.subplots(figsize=(10, 8), subplot_kw=dict(polar=True))
        
        # Plot data
        ax.plot(angles, team1_norm, 'o-', linewidth=2, label=team1, color='blue')
        ax.fill(angles, team1_norm, color='blue', alpha=0.25)
        
        ax.plot(angles, team2_norm, 'o-', linewidth=2, label=team2, color='red')
        ax.fill(angles, team2_norm, color='red', alpha=0.25)
        
        # Set labels
        cast(Any, ax).set_thetagrids(np.degrees(angles[:-1]), categories[:-1])
        
        # Add final score comparison
        plt.figtext(0.5, 0.01, f"Final Ranking: {team1} = {team1_data['final_ranking_score']:.2f}, "
                            f"{team2} = {team2_data['final_ranking_score']:.2f}",
                 ha='center', fontsize=12)
        
        plt.title(f"Team Comparison: {team1} vs {team2}", fontsize=16)
        plt.legend(loc='upper right', bbox_to_anchor=(1.2, 1.0))
        
        # Save or show
        if save_path:
            plt.savefig(save_path, dpi=300, bbox_inches='tight')
            logger.info(f"Saved plot to {save_path}")
        else:
            plt.show()