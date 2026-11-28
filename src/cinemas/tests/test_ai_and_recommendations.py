from unittest.mock import patch

import pytest
from django.urls import reverse
from rest_framework import status

from cinemas.models import Movie


@pytest.mark.django_db
def test_ai_movie_assistant_fallback_and_llm_modes(api_client, settings):
    m_scifi = Movie.objects.create(
        title='Interstellar',
        description='Space travel and relativity',
        genre=Movie.GenreChoices.SCI_FI,
        duration_minutes=169,
    )
    Movie.objects.create(
        title='The Hangover',
        description='Comedy trip',
        genre=Movie.GenreChoices.COMEDY,
        duration_minutes=100,
    )

    url = reverse('cinemas:movie-ai-assistant')

    # پرامپت خیلی کوتاه -> 400
    assert api_client.post(url, {'prompt': 'hi'}, format='json').status_code == status.HTTP_400_BAD_REQUEST

    # حالت Fallback وقتی کلید API خالی است
    settings.AI_API_KEY = ''
    res_fb = api_client.post(url, {'prompt': 'یه فیلم علمی تخیلی فضایی پیشنهاد بده', 'limit': 1}, format='json')
    assert res_fb.status_code == status.HTTP_200_OK
    assert res_fb.data['provider'] == 'fallback'
    assert res_fb.data['count'] == 1
    assert res_fb.data['recommended_movies'][0]['id'] == m_scifi.id

    # حالت LLM با ماک کردن پاسخ مدل
    settings.AI_API_KEY = 'fake-test-key'
    with patch(
        'cinemas.ai_service._call_openai_compatible_api',
        return_value={'answer': 'فیلم Interstellar بهترین انتخاب است.', 'recommended_movie_ids': [m_scifi.id]},
    ):
        res_llm = api_client.post(url, {'prompt': 'فیلم علمی تخیلی میخوام'}, format='json')
        assert res_llm.status_code == status.HTTP_200_OK
        assert res_llm.data['provider'] == 'llm'
        assert res_llm.data['recommended_movies'][0]['id'] == m_scifi.id


@pytest.mark.django_db
def test_recommended_movies_endpoint(api_client):
    movie = Movie.objects.create(
        title='Blade Runner 2049',
        description='Cyberpunk mystery',
        genre=Movie.GenreChoices.SCI_FI,
        duration_minutes=164,
    )

    mock_rec = {
        'strategy': 'popular',
        'movies': [movie],
        'scores': {movie.id: 9.5},
        'reasons': {movie.id: 'محبوب این هفته'},
        'cache_hit': False,
    }

    url = reverse('cinemas:movie-recommended')
    with patch('cinemas.api.v1.views.get_recommended_movies', return_value=mock_rec):
        res = api_client.get(url, {'limit': 5})
        assert res.status_code == status.HTTP_200_OK
        assert res['X-Cache'] == 'MISS'
        assert res.data['strategy'] == 'popular'
        assert res.data['results'][0]['recommendation_score'] == 9.5