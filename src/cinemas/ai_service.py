import json
import logging
import re
import urllib.error
import urllib.request
from django.conf import settings
from django.utils import timezone

from cinemas.models import Movie
from operations.models import Showtime

logger = logging.getLogger(__name__)

GENRE_KEYWORDS = {
    Movie.GenreChoices.ACTION: ['اکشن', 'هیجان', 'جنگی', 'مبارزه', 'action'],
    Movie.GenreChoices.COMEDY: ['کمدی', 'خنده', 'طنز', 'شاد', 'comedy', 'funny'],
    Movie.GenreChoices.DRAMA: ['درام', 'احساسی', 'اجتماعی', 'عاشقانه', 'drama'],
    Movie.GenreChoices.SCI_FI: ['علمی', 'تخیلی', 'فضا', 'آینده', 'scifi', 'sci-fi'],
    Movie.GenreChoices.THRILLER: ['معمایی', 'هیجان‌انگیز', 'جنایی', 'پلیسی', 'thriller'],
    Movie.GenreChoices.HORROR: ['ترسناک', 'وحشت', 'جن', 'horror'],
    Movie.GenreChoices.ANIMATION: ['انیمیشن', 'کارتون', 'کودک', 'خانوادگی', 'animation'],
}


def _collect_cinema_context(*, schema_name: str, max_movies: int = 25) -> tuple[list[Movie], set[int]]:
    movies = list(
        Movie.objects.filter(is_active=True)
        .select_related('created_by_cinema')
        .order_by('-created_at')[:max_movies]
    )
    upcoming_ids: set[int] = set()
    if schema_name != 'public' and movies:
        upcoming_ids = set(
            Showtime.objects.filter(
                movie_id__in=[m.id for m in movies],
                start_time__gte=timezone.now(),
            )
            .values_list('movie_id', flat=True)
            .distinct()
        )
    return movies, upcoming_ids


def _build_llm_messages(*, prompt: str, movies: list[Movie], upcoming_ids: set[int], limit: int) -> list[dict]:
    catalog = [
        {
            'id': m.id,
            'title': m.title,
            'genre': m.genre,
            'genre_fa': m.get_genre_display(),
            'duration_minutes': m.duration_minutes,
            'has_upcoming_showtime': m.id in upcoming_ids,
            'description': m.description[:220],
        }
        for m in movies
    ]

    system_prompt = (
        'تو دستیار هوشمند سینمای SeatMatrix هستی. '
        'فقط از میان فیلم‌های موجود در کاتالوگ زیر پیشنهاد بده و هرگز فیلمی خارج از لیست نساز. '
        'پاسخ را دقیقاً در قالب JSON معتبر با دو کلید برگردان: '
        '"answer" (پاسخ کوتاه و طبیعی به فارسی) و '
        f'"recommended_movie_ids" (لیستی حداکثر {limit} تایی از id عددی فیلم‌های پیشنهادی).\n\n'
        f'کاتالوگ فیلم‌های موجود:\n{json.dumps(catalog, ensure_ascii=False)}'
    )

    return [
        {'role': 'system', 'content': system_prompt},
        {'role': 'user', 'content': prompt},
    ]


def _extract_json_object(text: str) -> dict:
    cleaned = text.strip()
    match = re.search(r'\{.*\}', cleaned, re.DOTALL)
    if not match:
        raise ValueError('No JSON object found in LLM response')
    return json.loads(match.group(0))


def _call_openai_compatible_api(messages: list[dict]) -> dict:
    base_url = settings.AI_BASE_URL.rstrip('/')
    endpoint = f'{base_url}/chat/completions'

    payload = {
        'model': settings.AI_MODEL,
        'messages': messages,
        'temperature': 0.4,
    }

    req = urllib.request.Request(
        endpoint,
        data=json.dumps(payload).encode('utf-8'),
        headers={
            'Content-Type': 'application/json',
            'Authorization': f'Bearer {settings.AI_API_KEY}',
        },
        method='POST',
    )

    with urllib.request.urlopen(req, timeout=settings.AI_TIMEOUT_SECONDS) as resp:
        body = json.loads(resp.read().decode('utf-8'))

    content = body['choices'][0]['message']['content']
    return _extract_json_object(content)


def _fallback_recommend(*, prompt: str, movies: list[Movie], upcoming_ids: set[int], limit: int) -> tuple[str, list[Movie]]:
    lowered = prompt.lower()
    matched_genres = {
        genre
        for genre, words in GENRE_KEYWORDS.items()
        if any(word in lowered for word in words)
    }

    scored: list[tuple[int, Movie]] = []
    for movie in movies:
        score = 0
        if movie.genre in matched_genres:
            score += 5
        if movie.title.lower() in lowered:
            score += 6
        if movie.id in upcoming_ids:
            score += 2
        scored.append((score, movie))

    scored.sort(key=lambda item: (item[0], item[1].created_at), reverse=True)
    selected = [item[1] for item in scored[:limit]]

    if not selected:
        return 'در حال حاضر فیلم فعالی برای پیشنهاد وجود ندارد.', []

    titles = '، '.join(m.title for m in selected)
    answer = f'بر اساس درخواست شما، این فیلم‌ها را از لیست فعلی سینما پیشنهاد می‌کنم: {titles}.'
    return answer, selected


def ask_movie_assistant(*, prompt: str, schema_name: str, limit: int = 3) -> dict:
    movies, upcoming_ids = _collect_cinema_context(schema_name=schema_name)
    if not movies:
        return {
            'provider': 'fallback',
            'answer': 'در حال حاضر هیچ فیلم فعالی در سینما ثبت نشده است.',
            'movies': [],
        }

    movie_by_id = {m.id: m for m in movies}

    if getattr(settings, 'AI_API_KEY', ''):
        try:
            messages = _build_llm_messages(
                prompt=prompt,
                movies=movies,
                upcoming_ids=upcoming_ids,
                limit=limit,
            )
            parsed = _call_openai_compatible_api(messages)

            raw_ids = parsed.get('recommended_movie_ids', [])
            valid_movies = []
            for raw_id in raw_ids:
                try:
                    mid = int(raw_id)
                except (TypeError, ValueError):
                    continue
                if mid in movie_by_id and movie_by_id[mid] not in valid_movies:
                    valid_movies.append(movie_by_id[mid])
                if len(valid_movies) >= limit:
                    break

            answer = str(parsed.get('answer', '')).strip()
            if answer:
                return {
                    'provider': 'llm',
                    'answer': answer,
                    'movies': valid_movies,
                }
        except (urllib.error.URLError, TimeoutError, KeyError, ValueError, json.JSONDecodeError) as exc:
            logger.warning('AI provider failed, falling back to local recommender: %s', exc)

    answer, selected_movies = _fallback_recommend(
        prompt=prompt,
        movies=movies,
        upcoming_ids=upcoming_ids,
        limit=limit,
    )
    return {
        'provider': 'fallback',
        'answer': answer,
        'movies': selected_movies,
    }