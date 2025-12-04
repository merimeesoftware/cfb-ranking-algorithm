"""
Caching module for CFB Rankings API.
Provides both in-memory and file-based caching to reduce CFBD API calls.
"""
import os
import json
import hashlib
import time
from datetime import datetime, timedelta
from typing import Any, Optional, Dict
from functools import wraps
import threading

# Cache directory - use /tmp on Render (ephemeral but survives within deployment)
CACHE_DIR = os.environ.get('CACHE_DIR', os.path.join(os.path.dirname(__file__), '.cache'))

# Default TTL values in seconds
TTL_TEAMS = 24 * 60 * 60  # 24 hours - team info rarely changes
TTL_GAMES_HISTORICAL = 7 * 24 * 60 * 60  # 7 days - historical games don't change
TTL_GAMES_CURRENT = 60 * 60  # 1 hour - current season games update more frequently
TTL_RANKINGS = 30 * 60  # 30 minutes - computed rankings


class Cache:
    """Thread-safe caching with both memory and file-based storage."""
    
    def __init__(self, cache_dir: str = CACHE_DIR):
        self.cache_dir = cache_dir
        self._memory_cache: Dict[str, Dict[str, Any]] = {}
        self._lock = threading.RLock()
        self._ensure_cache_dir()
    
    def _ensure_cache_dir(self):
        """Create cache directory if it doesn't exist."""
        try:
            os.makedirs(self.cache_dir, exist_ok=True)
        except Exception as e:
            print(f"Warning: Could not create cache directory: {e}")
    
    def _generate_key(self, prefix: str, *args, **kwargs) -> str:
        """Generate a unique cache key from function arguments."""
        key_data = f"{prefix}:{args}:{sorted(kwargs.items())}"
        return hashlib.md5(key_data.encode()).hexdigest()
    
    def _get_cache_path(self, key: str) -> str:
        """Get file path for a cache key."""
        return os.path.join(self.cache_dir, f"{key}.json")
    
    def get(self, key: str) -> Optional[Any]:
        """Get value from cache (checks memory first, then file)."""
        with self._lock:
            # Check memory cache first
            if key in self._memory_cache:
                entry = self._memory_cache[key]
                if entry['expires_at'] > time.time():
                    return entry['data']
                else:
                    del self._memory_cache[key]
            
            # Check file cache
            cache_path = self._get_cache_path(key)
            if os.path.exists(cache_path):
                try:
                    with open(cache_path, 'r', encoding='utf-8') as f:
                        entry = json.load(f)
                    if entry['expires_at'] > time.time():
                        # Restore to memory cache
                        self._memory_cache[key] = entry
                        return entry['data']
                    else:
                        # Expired, remove file
                        os.remove(cache_path)
                except (json.JSONDecodeError, IOError, KeyError) as e:
                    print(f"Cache read error for {key}: {e}")
                    try:
                        os.remove(cache_path)
                    except:
                        pass
            
            return None
    
    def set(self, key: str, data: Any, ttl: int) -> None:
        """Store value in both memory and file cache."""
        with self._lock:
            expires_at = time.time() + ttl
            entry = {
                'data': data,
                'expires_at': expires_at,
                'created_at': time.time()
            }
            
            # Store in memory
            self._memory_cache[key] = entry
            
            # Store in file
            cache_path = self._get_cache_path(key)
            try:
                with open(cache_path, 'w', encoding='utf-8') as f:
                    json.dump(entry, f)
            except (IOError, TypeError) as e:
                print(f"Cache write error for {key}: {e}")
    
    def invalidate(self, key: str) -> None:
        """Remove a specific key from cache."""
        with self._lock:
            if key in self._memory_cache:
                del self._memory_cache[key]
            
            cache_path = self._get_cache_path(key)
            if os.path.exists(cache_path):
                try:
                    os.remove(cache_path)
                except IOError:
                    pass
    
    def invalidate_prefix(self, prefix: str) -> None:
        """Remove all cache entries matching a prefix."""
        with self._lock:
            # Clear from memory
            keys_to_remove = [k for k in self._memory_cache.keys() if k.startswith(prefix)]
            for key in keys_to_remove:
                del self._memory_cache[key]
            
            # Clear from files
            try:
                for filename in os.listdir(self.cache_dir):
                    if filename.endswith('.json'):
                        file_path = os.path.join(self.cache_dir, filename)
                        try:
                            with open(file_path, 'r', encoding='utf-8') as f:
                                entry = json.load(f)
                            # Check if this cache entry is for the prefix
                            # Since we hash keys, we can't easily match prefix
                            # For now, just let TTL handle cleanup
                        except:
                            pass
            except Exception:
                pass
    
    def clear_all(self) -> None:
        """Clear all cache entries."""
        with self._lock:
            self._memory_cache.clear()
            
            try:
                for filename in os.listdir(self.cache_dir):
                    if filename.endswith('.json'):
                        os.remove(os.path.join(self.cache_dir, filename))
            except Exception as e:
                print(f"Error clearing cache directory: {e}")
    
    def get_stats(self) -> Dict[str, Any]:
        """Get cache statistics."""
        with self._lock:
            memory_count = len(self._memory_cache)
            file_count = 0
            total_size = 0
            
            try:
                for filename in os.listdir(self.cache_dir):
                    if filename.endswith('.json'):
                        file_count += 1
                        total_size += os.path.getsize(os.path.join(self.cache_dir, filename))
            except Exception:
                pass
            
            return {
                'memory_entries': memory_count,
                'file_entries': file_count,
                'total_size_bytes': total_size,
                'cache_dir': self.cache_dir
            }


# Global cache instance
_cache = Cache()


def get_cache() -> Cache:
    """Get the global cache instance."""
    return _cache


def cached(prefix: str, ttl: int):
    """
    Decorator to cache function results.
    
    Args:
        prefix: Cache key prefix for this function
        ttl: Time-to-live in seconds
    """
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            cache = get_cache()
            
            # Generate cache key
            key = cache._generate_key(prefix, *args, **kwargs)
            
            # Try to get from cache
            cached_result = cache.get(key)
            if cached_result is not None:
                print(f"Cache HIT: {prefix}")
                return cached_result
            
            # Call function and cache result
            print(f"Cache MISS: {prefix}")
            result = func(*args, **kwargs)
            
            if result is not None:
                cache.set(key, result, ttl)
            
            return result
        return wrapper
    return decorator


def is_historical_season(year: int) -> bool:
    """Check if a season is historical (completed)."""
    now = datetime.now()
    # Season is historical if it's before the current year
    # or if current year and we're past January (bowl season over)
    if year < now.year:
        return True
    if year == now.year and now.month >= 2:
        # Could be considered historical after bowl season
        return False  # Still current until next season starts
    return False


def get_games_ttl(year: int) -> int:
    """Get appropriate TTL for games based on season."""
    if is_historical_season(year):
        return TTL_GAMES_HISTORICAL
    return TTL_GAMES_CURRENT
