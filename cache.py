"""
Pluggable cache backends for CFB Rankings API.
Default: file + memory. Optional: R2 when CACHE_BACKEND=r2 and R2 credentials set.
"""
import os
import json
import hashlib
import time
from abc import ABC, abstractmethod
from datetime import datetime
from typing import Any, Optional, Dict, List
from functools import wraps
import threading

CACHE_DIR = os.environ.get('CACHE_DIR', os.path.join(os.path.dirname(__file__), '.cache'))

TTL_TEAMS = 24 * 60 * 60
TTL_GAMES_HISTORICAL = 7 * 24 * 60 * 60
TTL_GAMES_CURRENT = 60 * 60
TTL_RANKINGS = 30 * 60
TTL_PRIORS = 7 * 24 * 60 * 60


class CacheBackend(ABC):
    @abstractmethod
    def get(self, key: str) -> Optional[Any]:
        pass

    @abstractmethod
    def set(self, key: str, data: Any, ttl: int) -> None:
        pass

    @abstractmethod
    def delete(self, key: str) -> None:
        pass

    @abstractmethod
    def clear_all(self) -> None:
        pass


class FileCacheBackend(CacheBackend):
    def __init__(self, cache_dir: str = CACHE_DIR):
        self.cache_dir = cache_dir
        os.makedirs(self.cache_dir, exist_ok=True)

    def _path(self, key: str) -> str:
        return os.path.join(self.cache_dir, f"{key}.json")

    def get(self, key: str) -> Optional[Any]:
        path = self._path(key)
        if not os.path.exists(path):
            return None
        try:
            with open(path, 'r', encoding='utf-8') as f:
                entry = json.load(f)
            if entry['expires_at'] > time.time():
                return entry['data']
            os.remove(path)
        except (json.JSONDecodeError, IOError, KeyError, OSError):
            try:
                os.remove(path)
            except OSError:
                pass
        return None

    def set(self, key: str, data: Any, ttl: int) -> None:
        entry = {'data': data, 'expires_at': time.time() + ttl, 'created_at': time.time()}
        try:
            with open(self._path(key), 'w', encoding='utf-8') as f:
                json.dump(entry, f)
        except (IOError, TypeError) as e:
            print(f"Cache write error for {key}: {e}")

    def delete(self, key: str) -> None:
        try:
            os.remove(self._path(key))
        except OSError:
            pass

    def clear_all(self) -> None:
        try:
            for filename in os.listdir(self.cache_dir):
                if filename.endswith('.json') and filename != '_index.json':
                    os.remove(os.path.join(self.cache_dir, filename))
        except OSError as e:
            print(f"Error clearing cache directory: {e}")


class R2CacheBackend(FileCacheBackend):
    """R2-backed cache using S3-compatible API. Falls back to local file if R2 unavailable."""

    def __init__(self):
        super().__init__(cache_dir=os.environ.get('CACHE_DIR', '/tmp/cfb-cache'))
        self._bucket = os.environ.get('R2_BUCKET_NAME')
        self._client = None
        try:
            import boto3
            if os.environ.get('R2_ACCESS_KEY_ID') and self._bucket:
                self._client = boto3.client(
                    's3',
                    endpoint_url=os.environ.get('R2_ENDPOINT_URL'),
                    aws_access_key_id=os.environ.get('R2_ACCESS_KEY_ID'),
                    aws_secret_access_key=os.environ.get('R2_SECRET_ACCESS_KEY'),
                )
        except ImportError:
            print("boto3 not installed; R2 cache uses local file fallback")

    def get(self, key: str) -> Optional[Any]:
        if self._client and self._bucket:
            try:
                obj = self._client.get_object(Bucket=self._bucket, Key=f"cache/{key}.json")
                entry = json.loads(obj['Body'].read().decode('utf-8'))
                if entry['expires_at'] > time.time():
                    return entry['data']
                self._client.delete_object(Bucket=self._bucket, Key=f"cache/{key}.json")
            except Exception:
                pass
        return super().get(key)

    def set(self, key: str, data: Any, ttl: int) -> None:
        entry = {'data': data, 'expires_at': time.time() + ttl, 'created_at': time.time()}
        if self._client and self._bucket:
            try:
                self._client.put_object(
                    Bucket=self._bucket,
                    Key=f"cache/{key}.json",
                    Body=json.dumps(entry).encode('utf-8'),
                )
            except Exception as e:
                print(f"R2 cache write error: {e}")
        super().set(key, data, ttl)


def create_cache_backend() -> CacheBackend:
    backend = os.environ.get('CACHE_BACKEND', 'file').lower()
    if backend == 'r2':
        return R2CacheBackend()
    return FileCacheBackend()


class Cache:
    """Thread-safe cache with memory layer, pluggable persistence, and prefix index."""

    def __init__(self, backend: Optional[CacheBackend] = None):
        self.backend = backend or create_cache_backend()
        self._memory_cache: Dict[str, Dict[str, Any]] = {}
        self._prefix_index: Dict[str, List[str]] = {}
        self._lock = threading.RLock()
        self._index_path = os.path.join(
            getattr(self.backend, 'cache_dir', CACHE_DIR), '_index.json'
        )
        self._load_index()

    def _load_index(self) -> None:
        try:
            if os.path.exists(self._index_path):
                with open(self._index_path, 'r', encoding='utf-8') as f:
                    self._prefix_index = json.load(f)
        except (json.JSONDecodeError, IOError):
            self._prefix_index = {}

    def _save_index(self) -> None:
        try:
            os.makedirs(os.path.dirname(self._index_path), exist_ok=True)
            with open(self._index_path, 'w', encoding='utf-8') as f:
                json.dump(self._prefix_index, f)
        except IOError as e:
            print(f"Cache index write error: {e}")

    def _generate_key(self, prefix: str, *args, **kwargs) -> str:
        key_data = f"{prefix}:{args}:{sorted(kwargs.items())}"
        return hashlib.md5(key_data.encode()).hexdigest()

    def _register_key(self, prefix: str, key: str) -> None:
        if prefix not in self._prefix_index:
            self._prefix_index[prefix] = []
        if key not in self._prefix_index[prefix]:
            self._prefix_index[prefix].append(key)
            self._save_index()

    def get(self, key: str) -> Optional[Any]:
        with self._lock:
            if key in self._memory_cache:
                entry = self._memory_cache[key]
                if entry['expires_at'] > time.time():
                    return entry['data']
                del self._memory_cache[key]

            data = self.backend.get(key)
            if data is not None:
                self._memory_cache[key] = {
                    'data': data,
                    'expires_at': time.time() + TTL_RANKINGS,
                }
            return data

    def set(self, key: str, data: Any, ttl: int, prefix: Optional[str] = None) -> None:
        with self._lock:
            expires_at = time.time() + ttl
            entry = {'data': data, 'expires_at': expires_at, 'created_at': time.time()}
            self._memory_cache[key] = entry
            self.backend.set(key, data, ttl)
            if prefix:
                self._register_key(prefix, key)

    def invalidate(self, key: str) -> None:
        with self._lock:
            self._memory_cache.pop(key, None)
            self.backend.delete(key)

    def invalidate_prefix(self, prefix: str) -> None:
        with self._lock:
            keys = list(self._prefix_index.get(prefix, []))
            for key in keys:
                self._memory_cache.pop(key, None)
                self.backend.delete(key)
            self._prefix_index[prefix] = []
            self._save_index()

    def clear_all(self) -> None:
        with self._lock:
            self._memory_cache.clear()
            self.backend.clear_all()
            self._prefix_index = {}
            self._save_index()

    def get_stats(self) -> Dict[str, Any]:
        with self._lock:
            file_count = len(self._prefix_index.get('games', [])) + len(
                self._prefix_index.get('rankings_computed', [])
            )
            return {
                'memory_entries': len(self._memory_cache),
                'indexed_prefixes': list(self._prefix_index.keys()),
                'file_entries': file_count,
                'cache_backend': os.environ.get('CACHE_BACKEND', 'file'),
                'cache_dir': getattr(self.backend, 'cache_dir', CACHE_DIR),
            }


_cache = Cache()


def get_cache() -> Cache:
    return _cache


def cached(prefix: str, ttl: int):
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            cache = get_cache()
            key = cache._generate_key(prefix, *args, **kwargs)
            cached_result = cache.get(key)
            if cached_result is not None:
                return cached_result
            result = func(*args, **kwargs)
            if result is not None:
                cache.set(key, result, ttl, prefix=prefix)
            return result
        return wrapper
    return decorator


def is_historical_season(year: int) -> bool:
    now = datetime.now()
    if year < now.year:
        return True
    if year == now.year:
        # Offseason: Jan-Jul treated as historical for completed prior season data
        if now.month < 8:
            return True
        return False
    return False


def get_games_ttl(year: int) -> int:
    if is_historical_season(year):
        return TTL_GAMES_HISTORICAL
    return TTL_GAMES_CURRENT
