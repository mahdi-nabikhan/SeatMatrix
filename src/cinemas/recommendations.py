from collections import Counter
from django.core.cache import cache
from django.db.models import Count
from django.utils import timezone

from cinemas.models import Movie
from operations.models import Showtime
from orders.models import Ticket

RECOMMENDATION_CACHE_TTL = 60 * 5  # 5 minutes


def _build_rec_cache_key(*, schema_name: str, user_id: int | None, limit: int) -> str:
    user_part = f'u{user_id}' if user_id else 'anon'
    return f'movies:recommended:{schema_name}:{user_part}:l{limit}'


def get_recommended_movies(*, user, schema_name: str, limit: int = 10) -> dict:

    user_id = user.id if (user and user.is_authenticated) else None
    cache_key = _build_rec_cache_key(schema_name=schema_name, user_id=user_id, limit=limit)

    cached = cache.get(cache_key)
    if cached is not None:
        return {**cached, 'cache_hit': True}

    active_movies = list(
        Movie.objects.filter(is_active=True).select_related('created_by_cinema')
    )
    if not active_movies:
        result = {'strategy': 'empty', 'movies': [], 'reasons': {}, 'scores': {}}
        return {**result, 'cache_hit': False}

    movie_map = {m.id: m for m in active_movies}

    if schema_name == 'public':
        ordered = sorted(active_movies, key=lambda m: m.created_at, reverse=True)[:limit]
        result = {
            'strategy': 'latest',
            'movies': ordered,
            'reasons': {m.id: 'جدیدترین فیلم‌ها' for m in ordered},
            'scores': {m.id: 1.0 for m in ordered},
        }
        cache.set(cache_key, result, timeout=RECOMMENDATION_CACHE_TTL)
        return {**result, 'cache_hit': False}

    now = timezone.now()

    upcoming_movie_ids = set(
        Showtime.objects.filter(start_time__gte=now)
        .values_list('movie_id', flat=True)
        .distinct()
    )

    popularity_rows = (
        Ticket.objects.filter(order__status='PAID')
        .values('showtime_seat__showtime__movie_id')
        .annotate(sold_count=Count('id'))
    )
    popularity_map = {
        row['showtime_seat__showtime__movie_id']: row['sold_count']
        for row in popularity_rows
    }

    watched_movie_ids: set[int] = set()
    preferred_genres: Counter = Counter()
    co_occurrence_counts: Counter = Counter()

    if user_id:
        watched_movie_ids = set(
            Ticket.objects.filter(
                order__customer__user_id=user_id,
                order__status='PAID',
            ).values_list('showtime_seat__showtime__movie_id', flat=True)
        )

        if watched_movie_ids:
            for mid in watched_movie_ids:
                movie = movie_map.get(mid)
                if movie:
                    preferred_genres[movie.genre] += 1

            similar_customer_ids = list(
                Ticket.objects.filter(
                    order__status='PAID',
                    showtime_seat__showtime__movie_id__in=watched_movie_ids,
                )
                .exclude(order__customer__user_id=user_id)
                .values_list('order__customer_id', flat=True)
                .distinct()[:100]
            )

            if similar_customer_ids:
                other_movie_ids = (
                    Ticket.objects.filter(
                        order__status='PAID',
                        order__customer_id__in=similar_customer_ids,
                    )
                    .exclude(showtime_seat__showtime__movie_id__in=watched_movie_ids)
                    .values_list('showtime_seat__showtime__movie_id', flat=True)
                )
                co_occurrence_counts.update(other_movie_ids)

    is_personalized = bool(watched_movie_ids)
    strategy = 'personalized' if is_personalized else 'trending'

    scored_items: list[tuple[float, Movie, str]] = []
    for movie in active_movies:
        if is_personalized and movie.id in watched_movie_ids:
            continue

        score = 0.0
        reason = 'پیشنهاد سینما'

        genre_weight = preferred_genres.get(movie.genre, 0) * 5.0
        collab_weight = co_occurrence_counts.get(movie.id, 0) * 3.0
        pop_weight = min(popularity_map.get(movie.id, 0), 50) * 0.5
        upcoming_weight = 2.0 if movie.id in upcoming_movie_ids else 0.0

        score = genre_weight + collab_weight + pop_weight + upcoming_weight

        if collab_weight > 0 and genre_weight > 0:
            reason = 'مطابق ژانر مورد علاقه شما و محبوب بین کاربران هم‌سلیقه'
        elif genre_weight > 0:
            reason = f'بر اساس علاقه‌ی شما به ژانر {movie.get_genre_display()}'
        elif collab_weight > 0:
            reason = 'محبوب بین خریداران مشابه'
        elif pop_weight > 0:
            reason = 'پرفروش در این سینما'
        elif upcoming_weight > 0:
            reason = 'در حال اکران در سانس‌های پیش‌رو'

        scored_items.append((score, movie, reason))

    scored_items.sort(key=lambda item: (item[0], item[1].created_at), reverse=True)
    top_items = scored_items[:limit]

    result = {
        'strategy': strategy,
        'movies': [item[1] for item in top_items],
        'scores': {item[1].id: round(item[0], 2) for item in top_items},
        'reasons': {item[1].id: item[2] for item in top_items},
    }
    cache.set(cache_key, result, timeout=RECOMMENDATION_CACHE_TTL)
    return {**result, 'cache_hit': False}