#!/usr/bin/env python3
# main.py
"""
Main application for the CFB Ranking System.
Provides a command-line interface to run the ranking system.
"""

import os
import sys
import logging
import argparse
import json
from datetime import datetime
from typing import Dict, List, Optional, Any, Union

from dotenv import load_dotenv
from tabulate import tabulate

from api_integration import CFBDApiClient
from data_processor import CFBDataProcessor
from ranking_algorithm import TeamQualityRanker
from visualizations import RankingVisualizer

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Default output directory for reports and charts
DEFAULT_OUTPUT_DIR = "ranking_results"

class CFBRankingApp:
    """
    Main application class for the CFB Ranking System.
    """
    
    def __init__(self, api_key: Optional[str] = None, output_dir: str = DEFAULT_OUTPUT_DIR):
        """
        Initialize the application.
        
        Args:
            api_key: Optional CFBD API key
            output_dir: Directory for output files
        """
        if api_key is None:
            load_dotenv()
            api_key = os.getenv('CFBD_API_KEY')
            if not api_key:
                raise ValueError("API key not found. Please set CFBD_API_KEY environment variable.")
        
        self.data_processor = CFBDataProcessor(api_key=api_key)
        self.output_dir = output_dir
        
        # Ensure output directory exists
        os.makedirs(output_dir, exist_ok=True)
    
    def run_ranking(self, 
                   year: int, 
                   week: Optional[int] = None,
                   use_ats: bool = False,
                   include_fcs: bool = True,
                   save_charts: bool = False,
                   config: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Run the ranking system for a specific season and optionally a specific week.
        
        Args:
            year: Season year
            week: Week number (None for full season)
            use_ats: Whether to use against-the-spread performance
            include_fcs: Whether to include FCS games
            save_charts: Whether to save charts to files
            config: Optional configuration overrides
            
        Returns:
            Dictionary with complete ranking data
        """
        logger.info(f"Running rankings for {year}" + (f" week {week}" if week else " full season"))
        
        # 1. Calculate Priors (History)
        # We need data from year-3, year-2, year-1
        priors = {}
        history_years = [year - 1, year - 2, year - 3]
        history_results = []
        
        logger.info("Fetching historical data for priors...")
        for h_year in history_years:
            try:
                logger.info(f"Processing {h_year}...")
                # Run full season for history year
                # We use a temporary ranker without priors for history to avoid infinite recursion
                # or just use the base tiers for the oldest year
                
                # Ideally we would chain them: Y-3 uses Y-6..Y-4 priors? 
                # For simplicity in V2.0, we'll run history years with base initialization
                # or we could implement a simplified run for history.
                
                # Let's run them with base config
                h_ranker = TeamQualityRanker(config=config)
                h_games = self.data_processor.get_games_for_season(h_year)
                h_games = self.data_processor.filter_games(h_games, include_fcs=include_fcs)
                
                # Process all games for history year
                for game in h_games:
                    h_ranker.update_quality_scores(game)
                
                history_results.append(h_ranker.calculate_final_rankings())
                
            except Exception as e:
                logger.warning(f"Could not fetch/process history for {h_year}: {e}")
        
        # Calculate priors from history
        if history_results:
            priors = TeamQualityRanker.calculate_priors(history_results)
            logger.info(f"Calculated priors for {len(priors)} teams")
        
        # 2. Initialize the ranking algorithm for Current Year
        ranking_config = config or {}
        ranking_config['use_ats'] = use_ats
        
        # V4.3: Dynamic Prior Strength
        # Formula: 0.2 * (1 - week/15) -> 20% at Week 0, 0% at Week 15
        if 'prior_strength' not in ranking_config:
             calc_week = week if week is not None else 15
             # Ensure week doesn't exceed 15 for calculation to avoid negative priors
             calc_week = min(calc_week, 15)
             ranking_config['prior_strength'] = max(0.0, 0.2 * (1.0 - (calc_week / 15.0)))
             logger.info(f"Using dynamic prior_strength: {ranking_config['prior_strength']:.3f} for week {calc_week}")

        ranker = TeamQualityRanker(config=ranking_config, priors=priors)
        
        # Fetch all game data
        raw_games = self.data_processor.get_games_for_season(year, through_week=week)
        logger.info(f"Fetched {len(raw_games)} games")
        
        # Filter games if needed
        filtered_games = self.data_processor.filter_games(
            games=raw_games,
            include_fcs=include_fcs
        )
        logger.info(f"Filtered to {len(filtered_games)} games")
        
        # Add betting lines if using ATS
        if use_ats:
            logger.info("Adding betting lines data...")
            betting_lines = self.data_processor.get_betting_lines(year, week)
            filtered_games = self.data_processor.enrich_games_with_betting_lines(
                filtered_games, betting_lines
            )
        
        # Organize games by week for sequential processing
        games_by_week = self.data_processor.organize_games_by_week(filtered_games)
        
        # 3. Iterative Solver
        # We run the season multiple times to allow scores to converge
        iterations = 4 # V4.0: 4 iterations
        
        final_ranks_ref = None # Reference ranks for opponent strength
        
        for i in range(iterations):
            logger.info(f"Iteration {i+1}/{iterations}...")
            
            # Reset ranker state for new iteration (keep priors and config)
            # We need to re-initialize the ranker but keep the same config/priors
            ranker = TeamQualityRanker(config=ranking_config, priors=priors)
            
            # Process games sequentially by week
            for week_num, weekly_games in sorted(games_by_week.items()):
                # Update team quality scores for each game
                for game in weekly_games:
                    ranker.update_quality_scores(game, reference_ranks=final_ranks_ref)
                
                # Save weekly scores for historical tracking (only on last iteration)
                if i == iterations - 1:
                    ranker.save_weekly_scores(week_num)
            
            # Calculate intermediate rankings to use as reference for next iteration
            current_results = ranker.calculate_final_rankings()
            # Extract just the scores for reference
            final_ranks_ref = {
                team: data['team_quality_score'] 
                for team, data in current_results['rankings'].items()
            }
        
        # Calculate final rankings after convergence
        rankings = ranker.calculate_final_rankings()
        
        # Add normalized scores
        normalized_rankings = ranker.normalize_scores(rankings)
        
        # Create output data
        result = {
            'year': year,
            'week': week,
            'run_date': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'config': {
                'use_ats': use_ats,
                'include_fcs': include_fcs,
                'power_conf_initial': ranker.power_conf_initial,
                'group_five_initial': ranker.group_five_initial,
                'fcs_initial': ranker.fcs_initial,
                'base_factor': ranker.base_factor,
                'conference_weight': ranker.conference_weight
            },
            'rankings': normalized_rankings,
            'ranker': ranker  # Store the ranker for visualizations
        }
        
        # Generate charts if requested
        if save_charts:
            self._generate_charts(result)
        
        return result
    
    def display_rankings(self, rankings_data: Dict[str, Any], top_n: Optional[int] = 25, show_all_divisions: bool = False):
        """
        Display the rankings in a formatted table.
        
        Args:
            rankings_data: Ranking data from run_ranking
            top_n: Number of teams to display (None for all)
            show_all_divisions: Whether to show all divisions or just FBS
        """
        # Extract normalized rankings
        # rankings_data['rankings'] contains the full structure from calculate_final_rankings
        # We need the 'rankings' key from that structure which maps team names to data
        full_rankings_data = rankings_data['rankings']
        
        # Filter for display if needed
        if not show_all_divisions:
            # We need to filter the list of teams, but visualizer takes a map
            # Let's filter the map passed to visualizer
            rankings_map = {
                team: data 
                for team, data in full_rankings_data['rankings'].items()
                if data.get('conference_type') in ['Power 4', 'Group of 5', 'FBS Independents']
            }
            print(f"\nDisplaying FBS teams only ({len(rankings_map)} teams). Use --all-divisions to see all.")
        else:
            rankings_map = full_rankings_data['rankings']
        
        # Create visualizer
        visualizer = RankingVisualizer()
        
        # Display rankings table
        table = visualizer.create_rankings_table(rankings_map, top_n=top_n)
        print("\nTeam Rankings:")
        print(table)
        
        # Display conference table
        conf_table = visualizer.create_conference_table(rankings_map)
        print("\nConference Rankings:")
        print(conf_table)
    
    def _generate_charts(self, rankings_data: Dict[str, Any]):
        """
        Generate and save charts for ranking results.
        
        Args:
            rankings_data: Ranking data from run_ranking
        """
        # Extract data
        year = rankings_data['year']
        week = rankings_data['week']
        # Extract the actual rankings map from the full structure
        full_rankings_data = rankings_data['rankings']
        rankings_map = full_rankings_data['rankings']
        ranker = rankings_data['ranker']
        
        # Create timestamp for filenames
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        
        # Create visualizer
        visualizer = RankingVisualizer()
        
        # Generate team rankings chart
        team_chart_path = os.path.join(
            self.output_dir, 
            f"team_rankings_{year}" + (f"_week{week}" if week else "") + f"_{timestamp}.png"
        )
        visualizer.plot_team_rankings(rankings_map, save_path=team_chart_path)
        
        # Generate conference rankings chart
        conf_chart_path = os.path.join(
            self.output_dir,
            f"conference_rankings_{year}" + (f"_week{week}" if week else "") + f"_{timestamp}.png"
        )
        visualizer.plot_conference_rankings(rankings_map, save_path=conf_chart_path)
        
        # Generate progression chart if we have weekly data
        prog_chart_path = None
        if ranker.weekly_scores:
            prog_chart_path = os.path.join(
                self.output_dir,
                f"team_progression_{year}" + (f"_week{week}" if week else "") + f"_{timestamp}.png"
            )
            visualizer.plot_quality_progression(ranker, save_path=prog_chart_path)
        
        logger.info(f"Generated charts in {self.output_dir}")
        
        return {
            'team_chart': team_chart_path,
            'conference_chart': conf_chart_path,
            'progression_chart': prog_chart_path
        }
    
    def save_rankings(self, rankings_data: Dict[str, Any], filename: Optional[str] = None) -> str:
        """
        Save rankings data to a JSON file.
        
        Args:
            rankings_data: Ranking data from run_ranking
            filename: Optional custom filename
            
        Returns:
            Path to the saved file
        """
        # Create a copy to remove non-serializable objects
        data_to_save = {
            'year': rankings_data['year'],
            'week': rankings_data['week'],
            'run_date': rankings_data['run_date'],
            'config': rankings_data['config'],
            'rankings': rankings_data['rankings']
        }
        
        # Generate filename if not provided
        if filename is None:
            year = rankings_data['year']
            week = rankings_data['week']
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            filename = f"rankings_{year}" + (f"_week{week}" if week else "") + f"_{timestamp}.json"
        
        # Ensure file has .json extension
        if not filename.endswith('.json'):
            filename += '.json'
        
        # Create full path
        filepath = os.path.join(self.output_dir, filename)
        
        # Save to file
        with open(filepath, 'w') as f:
            json.dump(data_to_save, f, indent=2)
        
        logger.info(f"Rankings saved to {filepath}")
        
        return filepath
    
    def compare_teams(self, rankings_data: Dict[str, Any], team1: str, team2: str):
        """
        Compare two teams and display their relative strengths.
        
        Args:
            rankings_data: Ranking data from run_ranking
            team1: First team name
            team2: Second team name
        """
        # Fix: Access the nested 'rankings' dictionary which maps team names to data
        rankings = rankings_data['rankings']['rankings']
        
        # Check if teams exist in rankings
        if team1 not in rankings or team2 not in rankings:
            print(f"Error: One or both teams not found in rankings.")
            return
        
        # Extract team data
        team1_data = rankings[team1]
        team2_data = rankings[team2]
        
        # Print comparison table
        comparison = [
            ["Team", team1, team2],
            ["Conference", team1_data['conference'], team2_data['conference']],
            ["Team Quality Score", f"{team1_data['team_quality_score']:.2f}", f"{team2_data['team_quality_score']:.2f}"],
            ["Conference Quality", f"{team1_data['conference_quality_score']:.2f}", f"{team2_data['conference_quality_score']:.2f}"],
            ["Final Ranking Score", f"{team1_data['final_ranking_score']:.2f}", f"{team2_data['final_ranking_score']:.2f}"],
            ["Overall Record", f"{team1_data['records']['total_wins']}-{team1_data['records']['total_losses']}", 
                            f"{team2_data['records']['total_wins']}-{team2_data['records']['total_losses']}"],
            ["Conf Record", f"{team1_data['records']['conf_wins']}-{team1_data['records']['conf_losses']}", 
                          f"{team2_data['records']['conf_wins']}-{team2_data['records']['conf_losses']}"],
            ["vs P5", f"{team1_data['records']['power_wins']}-{team1_data['records']['power_losses']}", 
                    f"{team2_data['records']['power_wins']}-{team2_data['records']['power_losses']}"],
            ["vs G5", f"{team1_data['records']['group_five_wins']}-{team1_data['records']['group_five_losses']}", 
                    f"{team2_data['records']['group_five_wins']}-{team2_data['records']['group_five_losses']}"],
            ["SOS", f"{team1_data['sos']:.2f}", f"{team2_data['sos']:.2f}"],
            ["Quality Wins", team1_data.get('quality_wins', 'N/A'), team2_data.get('quality_wins', 'N/A')],
            ["Bad Losses", team1_data.get('bad_losses', 'N/A'), team2_data.get('bad_losses', 'N/A')],
            ["Milestone Points", f"{team1_data.get('milestone_points', 0):.1f}", f"{team2_data.get('milestone_points', 0):.1f}"],
            ["Milestone Mult", f"{team1_data.get('milestone_mult', 1.0):.2f}x", f"{team2_data.get('milestone_mult', 1.0):.2f}x"]
        ]
        
        print("\nTeam Comparison:")
        print(tabulate(comparison, tablefmt="fancy_grid"))

        # Create visualizer and generate comparison chart
        visualizer = RankingVisualizer()
        
        # Display comparison chart
        # visualizer.create_team_matchup_chart(team1, team2, rankings)


def parse_args():
    """Parse command line arguments"""
    parser = argparse.ArgumentParser(description='CFB Ranking System')
    
    parser.add_argument('--year', type=int, required=True, help='Season year')
    parser.add_argument('--week', type=int, help='Week number (omit for full season)')
    parser.add_argument('--output-dir', default=DEFAULT_OUTPUT_DIR, help=f'Output directory (default: {DEFAULT_OUTPUT_DIR})')
    parser.add_argument('--save', action='store_true', help='Save rankings to file')
    parser.add_argument('--charts', action='store_true', help='Generate charts')
    parser.add_argument('--ats', action='store_true', help='Use Against The Spread performance')
    parser.add_argument('--exclude-fcs', action='store_true', help='Exclude FCS games')
    parser.add_argument('--all-divisions', action='store_true', help='Show all divisions in output (default: FBS only)')
    parser.add_argument('--top', type=int, default=25, help='Number of teams to display (default: 25)')
    parser.add_argument('--compare', nargs=2, metavar=('TEAM1', 'TEAM2'), help='Compare two teams')
    
    # Advanced configuration options
    adv_group = parser.add_argument_group('Advanced Configuration')
    adv_group.add_argument('--power-conf-initial', type=float, help='Initial quality score for Power conferences')
    adv_group.add_argument('--group5-initial', type=float, help='Initial quality score for Group of 5 conferences')
    adv_group.add_argument('--fcs-initial', type=float, help='Initial quality score for FCS conferences')
    adv_group.add_argument('--base-factor', type=float, help='Base adjustment factor (K)')
    adv_group.add_argument('--conference-weight', type=float, help='Weight of conference quality in final score')
    
    return parser.parse_args()


def main():
    """Main entry point for the application"""
    # Parse command line arguments
    args = parse_args()
    
    # Create the application
    try:
        app = CFBRankingApp(output_dir=args.output_dir)
        
        # Build advanced configuration if any options provided
        config = {}
        if args.power_conf_initial is not None:
            config['power_conf_initial'] = args.power_conf_initial
        if args.group5_initial is not None:
            config['group5_initial'] = args.group5_initial
        if args.fcs_initial is not None:
            config['fcs_initial'] = args.fcs_initial
        if args.base_factor is not None:
            config['base_factor'] = args.base_factor
        if args.conference_weight is not None:
            config['conference_weight'] = args.conference_weight
        
        # Run rankings
        rankings_data = app.run_ranking(
            year=args.year,
            week=args.week,
            use_ats=args.ats,
            include_fcs=not args.exclude_fcs,
            save_charts=args.charts,
            config=config or None
        )
        
        # Display rankings
        app.display_rankings(rankings_data, top_n=args.top, show_all_divisions=args.all_divisions)
        
        # Save rankings if requested
        if args.save:
            app.save_rankings(rankings_data)
        
        # Compare teams if requested
        if args.compare:
            app.compare_teams(rankings_data, args.compare[0], args.compare[1])
            
    except Exception as e:
        logger.error(f"Error: {e}")
        return 1
    
    return 0


if __name__ == "__main__":
    sys.exit(main())