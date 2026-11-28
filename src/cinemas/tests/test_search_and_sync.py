import urllib.error
from unittest.mock import patch
from django_tenants.utils import schema_context
import pytest
from django.urls import reverse
from rest_framework import status

from cinemas.models import Movie


@pytest.mark.django_db
def test_movie_search_uses_es_and_falls_back_to_db(api_client):
    m1 = Movie.objects.create(
        title='The Matrix',
        description='Simulated reality sci-fi',
        genre=Movie.GenreChoices.SCI_FI,
        duration_minutes=136,
    )
    Movie.objects.create(
        title='Toy Story',
        description='Family animation adventure',
        genre=Movie.GenreChoices.ANIMATION,
        duration_minutes=81,
    )

    url = reverse('cinemas:movie-search')


    with patch('cinemas.search._search_es', return_value=[m1.id]):
        res_es = api_client.get(url, {'q': 'matrix'})
        assert res_es.status_code == status.HTTP_200_OK
        assert res_es.data['engine'] == 'elasticsearch'
        assert res_es.data['count'] == 1
        assert res_es.data['results'][0]['id'] == m1.id


    with patch('cinemas.search._search_es', side_effect=urllib.error.URLError('ES down')):
        res_db = api_client.get(url, {'genre': Movie.GenreChoices.SCI_FI, 'min_duration': 100})
        assert res_db.status_code == status.HTTP_200_OK
        assert res_db.data['engine'] == 'database'
        assert res_db.data['count'] == 1
        assert res_db.data['results'][0]['id'] == m1.id


    res_bad = api_client.get(url, {'min_duration': 'not-an-int'})
    assert res_bad.status_code == status.HTTP_400_BAD_REQUEST


from django_tenants.utils import schema_context


@pytest.mark.django_db(transaction=True)
def test_movie_save_and_delete_signals_trigger_es_sync(make_tenant):
    tenant, _, _ = make_tenant('test_es_sync', 'ES Sync Cinema', 'es-sync.lvh.me')

    with patch('cinemas.signals.index_movie') as mock_index, \
         patch('cinemas.signals.delete_movie_from_index') as mock_delete:
        with schema_context(tenant.schema_name):
            movie = Movie.objects.create(
                title='Arrival',
                description='Linguistics sci-fi',
                genre=Movie.GenreChoices.SCI_FI,
                duration_minutes=116,
            )

            assert mock_index.called
            assert mock_index.call_args[0][0].id == movie.id

            movie_id = movie.id
            movie.delete()

        mock_delete.assert_called_once_with(movie_id)