import json
import logging
import os
import urllib.error
import urllib.request
from django.db.models import Q
from django.utils import timezone

from cinemas.models import Movie
from operations.models import Showtime

logger = logging.getLogger(__name__)

ELASTICSEARCH_URL = os.getenv('ELASTICSEARCH_URL', 'http://elasticsearch:9200').rstrip('/')
MOVIES_INDEX = os.getenv('ELASTICSEARCH_MOVIES_INDEX', 'movies')


def _get_showing_movie_ids(schema_name: str) -> set[int]:
    if schema_name == 'public':
        return set()
    return set(
        Showtime.objects.filter(start_time__gte=timezone.now())
        .values_list('movie_id', flat=True)
        .distinct()
    )


def _search_db(*, query: str, genre: str | None, min_duration: int | None,
               max_duration: int | None, only_showing: bool, schema_name: str) -> list[Movie]:
    qs = Movie.objects.filter(is_active=True).select_related('created_by_cinema')

    if query:
        qs = qs.filter(Q(title__icontains=query) | Q(description__icontains=query))
    if genre:
        qs = qs.filter(genre=genre)
    if min_duration is not None:
        qs = qs.filter(duration_minutes__gte=min_duration)
    if max_duration is not None:
        qs = qs.filter(duration_minutes__lte=max_duration)
    if only_showing:
        showing_ids = _get_showing_movie_ids(schema_name)
        qs = qs.filter(id__in=showing_ids)

    return list(qs.order_by('-created_at'))


def _search_es(*, query: str, genre: str | None, min_duration: int | None,
               max_duration: int | None, only_showing: bool, schema_name: str) -> list[int]:
    must = []
    filters = [{'term': {'is_active': True}}]

    if query:
        must.append({
            'multi_match': {
                'query': query,
                'fields': ['title^3', 'description'],
                'fuzziness': 'AUTO',
            }
        })
    if genre:
        filters.append({'term': {'genre': genre}})
    if min_duration is not None or max_duration is not None:
        duration_range = {}
        if min_duration is not None:
            duration_range['gte'] = min_duration
        if max_duration is not None:
            duration_range['lte'] = max_duration
        filters.append({'range': {'duration_minutes': duration_range}})
    if only_showing:
        showing_ids = list(_get_showing_movie_ids(schema_name))
        if not showing_ids:
            return []
        filters.append({'ids': {'values': [str(mid) for mid in showing_ids]}})

    body = {
        'size': 50,
        'query': {
            'bool': {
                'must': must or [{'match_all': {}}],
                'filter': filters,
            }
        },
    }

    req = urllib.request.Request(
        f'{ELASTICSEARCH_URL}/{MOVIES_INDEX}/_search',
        data=json.dumps(body).encode('utf-8'),
        headers={'Content-Type': 'application/json'},
        method='POST',
    )

    with urllib.request.urlopen(req, timeout=5) as resp:
        data = json.loads(resp.read().decode('utf-8'))

    hits = data.get('hits', {}).get('hits', [])
    return [int(hit['_id']) for hit in hits]


def search_movies(*, query: str = '', genre: str | None = None,
                  min_duration: int | None = None, max_duration: int | None = None,
                  only_showing: bool = False, schema_name: str = 'public') -> dict:
    try:
        movie_ids = _search_es(
            query=query,
            genre=genre,
            min_duration=min_duration,
            max_duration=max_duration,
            only_showing=only_showing,
            schema_name=schema_name,
        )
        movies_map = Movie.objects.filter(id__in=movie_ids, is_active=True).in_bulk()
        ordered_movies = [movies_map[mid] for mid in movie_ids if mid in movies_map]
        return {'engine': 'elasticsearch', 'movies': ordered_movies}
    except (urllib.error.URLError, TimeoutError, ValueError, KeyError) as exc:
        logger.warning('Elasticsearch search failed, falling back to DB: %s', exc)
        movies = _search_db(
            query=query,
            genre=genre,
            min_duration=min_duration,
            max_duration=max_duration,
            only_showing=only_showing,
            schema_name=schema_name,
        )
        return {'engine': 'database', 'movies': movies}
    
    
def ensure_movies_index() -> None:
    mapping = {
        'mappings': {
            'properties': {
                'title': {'type': 'text'},
                'description': {'type': 'text'},
                'genre': {'type': 'keyword'},
                'duration_minutes': {'type': 'integer'},
                'is_active': {'type': 'boolean'},
            }
        }
    }
    req = urllib.request.Request(
        f'{ELASTICSEARCH_URL}/{MOVIES_INDEX}',
        data=json.dumps(mapping).encode('utf-8'),
        headers={'Content-Type': 'application/json'},
        method='PUT',
    )
    try:
        with urllib.request.urlopen(req, timeout=5):
            pass
    except urllib.error.HTTPError as exc:
        if exc.code != 400:  # 400 = resource_already_exists_exception
            raise


def index_movie(movie: Movie) -> None:
    doc = {
        'title': movie.title,
        'description': movie.description or '',
        'genre': movie.genre,
        'duration_minutes': movie.duration_minutes,
        'is_active': movie.is_active,
    }
    req = urllib.request.Request(
        f'{ELASTICSEARCH_URL}/{MOVIES_INDEX}/_doc/{movie.id}?refresh=true',
        data=json.dumps(doc).encode('utf-8'),
        headers={'Content-Type': 'application/json'},
        method='PUT',
    )
    with urllib.request.urlopen(req, timeout=5):
        pass


def reindex_all_movies() -> int:
    ensure_movies_index()
    count = 0
    for movie in Movie.objects.all():
        index_movie(movie)
        count += 1
    return count