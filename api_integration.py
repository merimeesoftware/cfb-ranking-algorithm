# filepath: c:\Users\micha\DevProjects\CFB-Ranking-System\api_integration.py
# cfb_ranking_app/api_integration.py
from typing import Dict, List, Optional, Any
import os
from dotenv import load_dotenv
import requests
from cache import get_cache, TTL_TEAMS, TTL_GAMES_HISTORICAL, TTL_GAMES_CURRENT, get_games_ttl
from spend_guards import (
    CFBDOfflineError,
    cfbd_remaining_blocked,
    enforce_cfbd_remaining,
    is_cfbd_offline,
    register_live_cfbd_call,
    resolve_cfbd_api_key,
)


class CFBDRequestError(RuntimeError):
    """CFBD failed or returned an unusable body. Callers must not treat that as no games."""


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
                        "API key not found. Set CFBD_API_KEY."
                    )
        
        self.headers = {
            'Authorization': f'Bearer {api_key}',
            'accept': 'application/json'
        }
        self._cache = get_cache()
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
        if cfbd_remaining_blocked():
            raise CFBDOfflineError(
                'CFBD remaining calls are below the floor. Further live calls are stopped.'
            )

        try:
            call_n = register_live_cfbd_call()
            response = requests.get(url, headers=self.headers, params=params, timeout=30)
            remaining = enforce_cfbd_remaining(response.headers)
            print(
                f"CFBD LIVE #{call_n}: {endpoint} params={params} "
                f"status={response.status_code} remaining={remaining}"
            )
            if response.status_code in (401, 403):
                raise CFBDRequestError(
                    f'CFBD rejected the key for {endpoint} (HTTP {response.status_code})'
                )
            response.raise_for_status()
            payload = response.json()
        except CFBDOfflineError:
            raise
        except CFBDRequestError:
            raise
        except requests.exceptions.RequestException as e:
            status = None
            if getattr(e, 'response', None) is not None:
                status = e.response.status_code
            print(f"API Request Error to {endpoint}: HTTP {status}")
            raise CFBDRequestError(
                f'CFBD request failed for {endpoint} (HTTP {status})'
            ) from e
        except ValueError as e:
            print(f"API Request Error to {endpoint}: invalid JSON")
            raise CFBDRequestError(f'CFBD returned invalid JSON for {endpoint}') from e
        if payload is None:
            raise CFBDRequestError(f'CFBD returned an empty body for {endpoint}')
        return payload

    def _get_cache_key(self, prefix: str, *args, **kwargs) -> str:
        """Generate a cache key for an API call."""
        return self._cache._generate_key(prefix, *args, **kwargs)

    def get_games(
        self,
        year: int,
        week: Optional[int] = None,
        season_type: str = 'regular',
        refresh: bool = False,
    ) -> List[Dict]:
        """Fetch games with caching, error handling and data transformation.

        ``refresh`` skips a restored snapshot. The current-season cron sets it
        so a 30-day cache entry cannot hide the next Sunday's games.
        """
        cache_key = self._get_cache_key('games', year, week, season_type)

        if not refresh:
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
        if not isinstance(games, list):
            raise CFBDRequestError('CFBD /games did not return a list')
        result = [self._transform_game(game) for game in games if self._is_valid_game(game)]
        
        # Cache with appropriate TTL
        if result:
            ttl = get_games_ttl(year)
            self._cache.set(cache_key, result, ttl, prefix='games')
        
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
        if not isinstance(teams, list):
            raise CFBDRequestError('CFBD /teams did not return a list')
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
        if not isinstance(result, list):
            raise CFBDRequestError('CFBD /lines did not return a list')

        if result:
            ttl = get_games_ttl(year)
            self._cache.set(cache_key, result, ttl, prefix='betting_lines')
        
        return result

    def _transform_game(self, game: Dict) -> Dict:
        """Transform CFBD game dict to internal format"""
        return {
            'id': game.get('id'),
            'completed': game.get('completed'),
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
            game.get('homeTeam') is not None
            and game.get('awayTeam') is not None
        )
