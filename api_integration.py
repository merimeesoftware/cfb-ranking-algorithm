# filepath: c:\Users\micha\DevProjects\CFB-Ranking-System\api_integration.py
# cfb_ranking_app/api_integration.py
from typing import Dict, List, Optional, Any
import os
from dotenv import load_dotenv
import requests
from cache import get_cache, TTL_TEAMS, TTL_GAMES_HISTORICAL, TTL_GAMES_CURRENT, get_games_ttl

class CFBDApiClient:
    """Centralized API client for CFBD data using direct HTTP requests"""
    
    BASE_URL = "https://api.collegefootballdata.com"
    
    def __init__(self, api_key: Optional[str] = None):
        if api_key is None:
            load_dotenv()
            api_key = os.getenv('CFBD_API_KEY')
            if not api_key:
                raise ValueError("API key not found in environment variables")
        
        # print(f"DEBUG: Using API Key: {api_key[:5]}...") 
        self.headers = {
            'Authorization': f'Bearer {api_key}',
            'accept': 'application/json'
        }
        self._cache = get_cache()

    def _make_request(self, endpoint: str, params: Dict[str, Any] = None) -> Any:
        """Helper to make API requests with error handling"""
        url = f"{self.BASE_URL}{endpoint}"
        # print(f"DEBUG: Requesting {url} with params {params}")
        try:
            response = requests.get(url, headers=self.headers, params=params, timeout=30)
            response.raise_for_status()
            data = response.json()
            # print(f"DEBUG: Response type: {type(data)}, Length: {len(data) if isinstance(data, list) else 'N/A'}")
            # if isinstance(data, list) and len(data) > 0:
            #     print(f"DEBUG: First item keys: {data[0].keys()}")
            return data
        except requests.exceptions.RequestException as e:
            print(f"API Request Error to {endpoint}: {e}")
            if hasattr(e, 'response') and e.response is not None:
                print(f"Response: {e.response.text}")
            return []

    def _get_cache_key(self, prefix: str, *args, **kwargs) -> str:
        """Generate a cache key for an API call."""
        return self._cache._generate_key(prefix, *args, **kwargs)

    def get_games(self, year: int, week: Optional[int] = None, season_type: str = 'regular') -> List[Dict]:
        """Fetch games with caching, error handling and data transformation"""
        cache_key = self._get_cache_key('games', year, week, season_type)
        
        # Try cache first
        cached = self._cache.get(cache_key)
        if cached is not None:
            print(f"Cache HIT: games {year} week={week} type={season_type}")
            return cached
        
        print(f"Cache MISS: games {year} week={week} type={season_type}")
        
        params = {
            'year': year,
            'seasonType': season_type
        }
        if week is not None:
            params['week'] = week

        games = self._make_request('/games', params)
        result = [self._transform_game(game) for game in games if self._is_valid_game(game)]
        
        # Cache with appropriate TTL
        if result:
            ttl = get_games_ttl(year)
            self._cache.set(cache_key, result, ttl)
        
        return result

    def get_team_info(self) -> Dict[str, str]:
        """Fetch team conference affiliations with caching"""
        cache_key = self._get_cache_key('team_info')
        
        cached = self._cache.get(cache_key)
        if cached is not None:
            print("Cache HIT: team_info")
            return cached
        
        print("Cache MISS: team_info")
        teams = self._make_request('/teams/fbs')
        result = {team['school']: team['conference'] for team in teams}
        
        if result:
            self._cache.set(cache_key, result, TTL_TEAMS)
        
        return result

    def get_teams_with_logos(self) -> Dict[str, Dict[str, Any]]:
        """Fetch all team info including logos and colors with caching"""
        cache_key = self._get_cache_key('teams_with_logos')
        
        cached = self._cache.get(cache_key)
        if cached is not None:
            print("Cache HIT: teams_with_logos")
            return cached
        
        print("Cache MISS: teams_with_logos")
        teams = self._make_request('/teams')
        result = {}
        for team in teams:
            result[team['school']] = {
                'id': team.get('id'),
                'conference': team.get('conference'),
                'mascot': team.get('mascot'),
                'abbreviation': team.get('abbreviation'),
                'color': team.get('color'),
                'alt_color': team.get('alternateColor'),
                'logos': team.get('logos', []),
                'classification': team.get('classification')
            }
        
        if result:
            self._cache.set(cache_key, result, TTL_TEAMS)
        
        return result

    def get_rankings(self, year: int, week: Optional[int] = None) -> List[Dict]:
        """Fetch team rankings with caching"""
        cache_key = self._get_cache_key('rankings', year, week)
        
        cached = self._cache.get(cache_key)
        if cached is not None:
            print(f"Cache HIT: rankings {year} week={week}")
            return cached
        
        print(f"Cache MISS: rankings {year} week={week}")
        params = {'year': year}
        if week is not None:
            params['week'] = week
            
        result = self._make_request('/rankings', params)
        
        if result:
            ttl = get_games_ttl(year)  # Use same TTL logic as games
            self._cache.set(cache_key, result, ttl)
        
        return result
            
    def get_betting_lines(self, year: int, week: Optional[int] = None) -> List[Dict]:
        """Fetch betting lines and spreads with caching"""
        cache_key = self._get_cache_key('betting_lines', year, week)
        
        cached = self._cache.get(cache_key)
        if cached is not None:
            print(f"Cache HIT: betting_lines {year} week={week}")
            return cached
        
        print(f"Cache MISS: betting_lines {year} week={week}")
        params = {
            'year': year,
            'seasonType': 'regular'
        }
        if week is not None:
            params['week'] = week
            
        result = self._make_request('/lines', params)
        
        if result:
            ttl = get_games_ttl(year)
            self._cache.set(cache_key, result, ttl)
        
        return result

    def _transform_game(self, game: Dict) -> Dict:
        """Transform CFBD game dict to internal format"""
        return {
            'week': game.get('week'),
            'year': game.get('season'),
            'home_team_name': game.get('homeTeam'),
            'away_team_name': game.get('awayTeam'),
            'home_score': game.get('homePoints'),
            'away_score': game.get('awayPoints'),
            'home_conference': game.get('homeConference'),
            'away_conference': game.get('awayConference'),
            'is_interconference': game.get('homeConference') != game.get('awayConference'),
            'venue': game.get('venue'),
            'date': game.get('startDate')
        }

    @staticmethod
    def _is_valid_game(game: Dict) -> bool:
        """Validate game has required data"""
        return (
            game.get('homePoints') is not None 
            and game.get('awayPoints') is not None
            and game.get('homeTeam') is not None
            and game.get('awayTeam') is not None
        )
