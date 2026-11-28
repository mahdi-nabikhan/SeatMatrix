import hashlib
import uuid
from django.core.cache import cache
from django_tenants.utils import schema_context

MOVIE_LIST_TTL = 60 * 10    # 10 minutes
MOVIE_DETAIL_TTL = 60 * 15  # 15 minutes

LIST_VERSION_KEY = 'movies:list:version'
DETAIL_VERSION_KEY_PREFIX = 'movies:detail:version'


def _get_or_init_version(key: str) -> str:
    """Return an existing cache namespace version token or initialize a new one."""
    version = cache.get(key)
    if not version:
        version = uuid.uuid4().hex[:8]
        cache.set(key, version, timeout=None)
    return version


def _build_list_key(host: str, full_path: str) -> str:
    """Build a versioned cache key for a host and query-string-specific movie list."""
    version = _get_or_init_version(LIST_VERSION_KEY)
    raw = f'{host}:{full_path}'.encode('utf-8')
    digest = hashlib.md5(raw).hexdigest()
    return f'movies:list:v{version}:{digest}'


def _build_detail_key(movie_id: int, host: str) -> str:
    """Build a versioned cache key for a single movie detail response."""
    version_key = f'{DETAIL_VERSION_KEY_PREFIX}:{movie_id}'
    version = _get_or_init_version(version_key)
    return f'movies:detail:{movie_id}:v{version}:{host}'


def get_cached_movie_list(*, host: str, full_path: str):
    """Fetch cached movie list payload from the shared public cache namespace."""
    with schema_context('public'):
        key = _build_list_key(host, full_path)
        return cache.get(key)


def set_cached_movie_list(*, host: str, full_path: str, data) -> None:
    """Store serialized movie list payload in the shared public cache namespace."""
    with schema_context('public'):
        key = _build_list_key(host, full_path)
        cache.set(key, data, timeout=MOVIE_LIST_TTL)


def get_cached_movie_detail(*, movie_id: int, host: str):
    """Fetch cached movie detail payload for the given movie ID and host."""
    with schema_context('public'):
        key = _build_detail_key(movie_id, host)
        return cache.get(key)


def set_cached_movie_detail(*, movie_id: int, host: str, data) -> None:
    """Store serialized movie detail payload for the given movie ID and host."""
    with schema_context('public'):
        key = _build_detail_key(movie_id, host)
        cache.set(key, data, timeout=MOVIE_DETAIL_TTL)


def invalidate_movie_caches(*, movie_id: int | None = None) -> None:
    """Bump cache version keys to invalidate movie list and optional detail entries."""
    
    with schema_context('public'):
        new_version = uuid.uuid4().hex[:8]
        cache.set(LIST_VERSION_KEY, new_version, timeout=None)
        if movie_id is not None:
            cache.set(f'{DETAIL_VERSION_KEY_PREFIX}:{movie_id}', new_version, timeout=None)