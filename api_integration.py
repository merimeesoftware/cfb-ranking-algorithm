# filepath: c:\Users\micha\DevProjects\CFB-Ranking-System\api_integration.py
# cfb_ranking_app/api_integration.py
from typing import Dict, List, Optional, Any
import os
from dotenv import load_dotenv
import requests
from cache import get_cache, TTL_TEAMS, TTL_GAMES_HISTORICAL, TTL_GAMES_CURRENT, get_games_ttl
from spend_guards import (
    CFBDOfflineError,
    is_cfbd_offline,
    register_live_cfbd_call,
    resolve_cfbd_api_key,
)


class CFBDApiClient:
    """Centralized API client for CFBD data using direct HTTP requests"""
    
    BASE_URL = "https://api.collegefootballdata.com"
    
    def __init__(self, api_key: Optional[str] = None):
        if api_key is None:
            load_dotenv()
            api_key = resolve_cfbd_api_key()
            if not api_key:
                # Offline / fixture workflows may construct the client with a dummy key
                api_key = 'offline-placeholder'
                if not is_cfbd_offline():
                    raise ValueError(
                        "API key not found. Set CFBD_API_KEY (slot A) and/or "
                        "CFBD_API_KEY_B (slot B); choose with CFBD_API_KEY_SLOT=A|B."
                    )
        
        self.headers = {
            'Authorization': f'Bearer {api_key}',
            'accept': 'application/json'
        }
        self._cache = get_cache()
        self._key_suffix = (api_key[-4:] if api_key and api_key != 'offline-placeholder' else 'none')
    def _make_request(self, endpoint: str, params: Dict[str, Any] = None) -> Any:
        """Helper to make API requests with error handling and spend guards."""
        url = f"{self.BASE_URL}{endpoint}"
        if is_cfbd_offline():
            print(
                f"CFBD OFFLINE: blocked live request {endpoint} params={params}. "
                "Use cache/static or set CFBD_OFFLINE=0."
            )
            raise CFBDOfflineError(
                f'CFBD offline: refused live call to {endpoint}. '
                'Serve static rankings or warm .cache/ first.'
            )

        try:
            call_n = register_live_cfbd_call()
            response = requests.get(url, headers=self.headers, params=params, timeout=30)
            remaining = response.headers.get('X-CallLimit-Remaining')
            print(
                f"CFBD LIVE #{call_n}: {endpoint} params={params} "
                f"status={response.status_code} remaining={remaining} "
                f"key=…{self._key_suffix}"
            )
            response.raise_for_status()
            return response.json()
        except CFBDOfflineError:
            raise
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

        try:
            games = self._make_request('/games', params)
        except CFBDOfflineError as e:
            print(f"CFBD offline on games miss: {e}")
            return []
        result = [self._transform_game(game) for game in games if self._is_valid_game(game)]
        
        # Cache with appropriate TTL
        if result:
            ttl = get_games_ttl(year)
            self._cache.set(cache_key, result, ttl, prefix='games')
        
        return result

    def get_team_info(self) -> Dict[str, str]:
        """Fetch team conference affiliations with caching"""
        cache_key = self._get_cache_key('team_info')
        
        cached = self._cache.get(cache_key)
        if cached is not None:
            print("Cache HIT: team_info")
            return cached
        
        print("Cache MISS: team_info")
        try:
            teams = self._make_request('/teams/fbs')
        except CFBDOfflineError as e:
            print(f"CFBD offline on team_info miss: {e}")
            return {}
        result = {team['school']: team['conference'] for team in teams}
        
        if result:
            self._cache.set(cache_key, result, TTL_TEAMS, prefix='teams')
        
        return result

    def get_teams_with_logos(self) -> Dict[str, Dict[str, Any]]:
        """Fetch all team info including logos and colors with caching"""
        cache_key = self._get_cache_key('teams_with_logos')
        
        cached = self._cache.get(cache_key)
        if cached is not None:
            print("Cache HIT: teams_with_logos")
            return cached
        
        print("Cache MISS: teams_with_logos")
        try:
            teams = self._make_request('/teams')
        except CFBDOfflineError as e:
            print(f"CFBD offline on teams_with_logos miss: {e}")
            return {}
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
            self._cache.set(cache_key, result, TTL_TEAMS, prefix='teams')
        
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

        try:
            result = self._make_request('/rankings', params)
        except CFBDOfflineError as e:
            print(f"CFBD offline on rankings miss: {e}")
            return []
        
        if result:
            ttl = get_games_ttl(year)
            self._cache.set(cache_key, result, ttl, prefix='rankings_api')
        
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

        try:
            result = self._make_request('/lines', params)
        except CFBDOfflineError as e:
            print(f"CFBD offline on betting_lines miss: {e}")
            return []
        
        if result:
            ttl = get_games_ttl(year)
            self._cache.set(cache_key, result, ttl, prefix='betting_lines')
        
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
            'date': game.get('startDate'),
            # Required for HFA / postseason K / champ anchors in TeamQualityRanker
            'notes': game.get('notes') or '',
            'season_type': game.get('seasonType') or 'regular',
            'neutral_site': bool(game.get('neutralSite')),
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
