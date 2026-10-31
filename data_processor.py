# filepath: c:\Users\micha\DevProjects\CFB-Ranking-System\data_processor.py
from typing import List, Dict, Any, Optional, Union
from collections import defaultdict
from pathlib import Path
from api_integration import CFBDApiClient

# --- Conference Classification Constants ---
POWER_4_CONFERENCES = {
    "SEC", "Big Ten", "ACC", "Big 12", "Pac-12"
}
GROUP_OF_5_CONFERENCES = {
    "American Athletic", "Conference USA", "Mid-American", "Mountain West", "Sun Belt"
}

class CFBDataProcessor:
    """
    Handles fetching, cleaning, and organizing college football game data.
    """
    
    def __init__(self, api_key: Optional[str] = None, api_client: Optional[CFBDApiClient] = None):
        """
        Initialize the data processor.
        
        Args:
            api_key: CFBD API key (used if api_client is not provided)
            api_client: Existing CFBDApiClient instance
        """
        if api_client:
            self.api_client = api_client
        else:
            self.api_client = CFBDApiClient(api_key=api_key)

        self.team_conference_map = {}
        self.team_info_map = {}  # Full team info including logos

    def _initialize_conference_map(self):
        """Load teams when a compute path asks. Import does not call this."""
        self.ensure_teams()

    def ensure_teams(
        self,
        season: Optional[int] = None,
        *,
        persist: bool = False,
        root: Optional[Union[str, Path]] = None,
    ) -> None:
        """Use the season file when it exists. Otherwise one /teams call."""
        if self.team_info_map:
            return
        stored = None
        if season is not None:
            from static_rankings import read_season_teams
            stored = read_season_teams(season, root=root)
        if stored:
            self.team_info_map = stored
        else:
            self.team_info_map = self.api_client.get_teams_with_logos() or {}
            if persist and season is not None and self.team_info_map:
                from static_rankings import write_season_teams
                write_season_teams(season, self.team_info_map, root=root)
        self.team_conference_map = {
            team: info.get('conference')
            for team, info in self.team_info_map.items()
            if isinstance(info, dict)
        }

    def get_team_logo(self, team_name: str) -> Optional[str]:
        """Get the primary logo URL for a team."""
        info = self.team_info_map.get(team_name, {})
        logos = info.get('logos', [])
        return logos[0] if logos else None

    def get_team_color(self, team_name: str) -> Optional[str]:
        """Get the primary color for a team."""
        info = self.team_info_map.get(team_name, {})
        return info.get('color')

    def get_conference_type(self, conference_name: Optional[str]) -> str:
        """Classifies a conference name into Power 4, Group of 5, or FCS."""
        if conference_name in POWER_4_CONFERENCES:
            return "Power 4"
        elif conference_name in GROUP_OF_5_CONFERENCES:
            return "Group of 5"
        elif conference_name == "FBS Independents":
            return "Power 4"  # V4.0.1: Independents compete at P4 level (ND, Army, etc.)
        else: 
            return "FCS"

    def get_games_for_season(
        self,
        year: int,
        through_week: Optional[int] = None,
        use_week_scoped_fetch: bool = True,
    ) -> List[Dict[str, Any]]:
        """
        One bulk ``/games?year=Y&seasonType=both`` call, then filter in process.

        ``use_week_scoped_fetch`` is ignored. Per-week and regular-plus-postseason
        pairs used to multiply calls. Postseason rows stay out of weeks 1–14.
        CFBD errors propagate; an empty list means the season had no games.
        """
        del use_week_scoped_fetch
        self.ensure_teams(year)
        raw_games = self.api_client.get_games(year=year, season_type='both')
        selected: List[Dict[str, Any]] = []
        for game in raw_games:
            season_type = game.get('season_type') or 'regular'
            week = game.get('week')
            if season_type == 'postseason':
                if through_week is None or through_week >= 15:
                    selected.append(game)
                continue
            if through_week is not None and (week is None or week > through_week):
                continue
            selected.append(game)
        return self._process_raw_games(selected)

    def get_available_weeks(self, year: int) -> List[int]:
        """Return sorted regular-season week numbers. One bulk games call."""
        self.ensure_teams(year)
        games = self.api_client.get_games(year=year, season_type='both')
        weeks = sorted({
            g['week'] for g in games
            if g.get('week') is not None and (g.get('season_type') or 'regular') == 'regular'
        })
        return weeks if weeks else list(range(1, 16))

    def _process_raw_games(self, games: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Process raw game data to add conference types and other metadata.
        """
        processed_games = []
        for game in games:
            home_team = game.get('home_team_name')
            away_team = game.get('away_team_name')
            
            if game.get('completed') is False:
                continue
            if not home_team or not away_team or game.get('home_score') is None or game.get('away_score') is None:
                continue

            # Get conferences from the map, fallback to game data
            home_conf = self.team_conference_map.get(home_team, game.get('home_conference'))
            away_conf = self.team_conference_map.get(away_team, game.get('away_conference'))

            # Determine conference types
            home_conf_type = self.get_conference_type(home_conf)
            away_conf_type = self.get_conference_type(away_conf)

            processed_game = {
                **game,
                'home_conference': home_conf,
                'away_conference': away_conf,
                'home_conference_type': home_conf_type,
                'away_conference_type': away_conf_type,
                'spread_info': None 
            }
            processed_games.append(processed_game)

        return processed_games

    def filter_games(self, games: List[Dict[str, Any]], include_fcs: bool = True) -> List[Dict[str, Any]]:
        """
        Filter games based on criteria (e.g., exclude FCS matchups).
        """
        if include_fcs:
            return games
        
        filtered = []
        for game in games:
            # Keep game if BOTH teams are NOT FCS (i.e. FBS vs FBS)
            # Or maybe keep if AT LEAST ONE is FBS? 
            # Standard ranking usually cares about FBS vs FBS.
            # Let's keep if at least one is FBS to count wins against FCS?
            # The prompt said "Exclude FCS games", usually implies games involving FCS teams.
            # But for rankings, wins vs FCS count less but still exist.
            # If the flag is "exclude_fcs", let's assume we only want FBS vs FBS.
            if game['home_conference_type'] == 'FCS' or game['away_conference_type'] == 'FCS':
                continue
            filtered.append(game)
        return filtered

    def get_betting_lines(self, year: int, week: Optional[int] = None) -> List[Dict[str, Any]]:
        """Fetch betting lines from API."""
        return self.api_client.get_betting_lines(year, week)

    def enrich_games_with_betting_lines(self, games: List[Dict[str, Any]], betting_lines: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Match betting lines to games and add spread info.
        """
        # Create a lookup for betting lines to optimize
        # Key: (home_team, away_team, week) -> line
        lines_map = {}
        for line in betting_lines:
            # Ensure we have necessary attributes
            if isinstance(line, dict):
                 key = (line.get('home_team'), line.get('away_team'), line.get('week'))
                 lines_map[key] = line
            # Fallback for object-like access if needed (though type hint says Dict)
            elif hasattr(line, 'home_team') and hasattr(line, 'away_team') and hasattr(line, 'week'):
                 key = (line.home_team, line.away_team, line.week)
                 lines_map[key] = line

        for game in games:
            key = (game['home_team_name'], game['away_team_name'], game['week'])
            line = lines_map.get(key)
            
            if line:
                # Extract spread
                # Assuming line structure matches CFBD API response
                lines_data = line.lines if hasattr(line, 'lines') else line.get('lines', [])
                if lines_data and len(lines_data) > 0:
                    # Get first provider's line
                    game_line = lines_data[0]
                    spread = game_line.spread if hasattr(game_line, 'spread') else game_line.get('spread')
                    
                    if spread is not None:
                        # CFBD spread is usually negative for favorite?
                        # Let's store it as: favorite team and absolute spread
                        # If spread is -7 for Home, Home is favorite by 7.
                        # If spread is 7 for Home, Away is favorite by 7.
                        
                        # Actually CFBD documentation says: "Spread for the home team"
                        # -7 means Home is favored by 7.
                        
                        is_home_fav = spread < 0
                        favorite = game['home_team_name'] if is_home_fav else game['away_team_name']
                        abs_spread = abs(spread)
                        
                        game['spread_info'] = {
                            'favorite': favorite,
                            'spread': abs_spread,
                            'raw_spread': spread
                        }

        return games

    def organize_games_by_week(self, games: List[Dict[str, Any]]) -> Dict[int, List[Dict[str, Any]]]:
        """Group games by week number."""
        games_by_week = defaultdict(list)
        for game in games:
            games_by_week[game['week']].append(game)
        return dict(games_by_week)

# Legacy function for backward compatibility if needed (or can be removed)
def process_data(games_data: List[Dict[str, Any]], team_conference_map: Dict[str, str]) -> List[Dict[str, Any]]:
    processor = CFBDataProcessor(api_key="dummy") # API key not needed for this specific method logic if map provided
    processor.team_conference_map = team_conference_map
    # We need to adapt the input to match what _process_raw_games expects if it differs, 
    # but here it's mostly compatible.
    return processor._process_raw_games(games_data)


