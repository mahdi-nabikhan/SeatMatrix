from unittest.mock import patch

import pytest
from django.db.models import ProtectedError
from django.urls import reverse
from rest_framework import status

from cinemas.models import Movie


@pytest.mark.django_db
def test_movie_list_and_detail_caching_hit_miss(api_client, public_tenant):
    cinema, _ = public_tenant
    movie = Movie.objects.create(
        title='Dune',
        description='Desert planet sci-fi epic',
        genre=Movie.GenreChoices.SCI_FI,
        duration_minutes=155,
        created_by_cinema=cinema,
    )

    list_url = reverse('cinemas:movie-list')
    detail_url = reverse('cinemas:movie-detail', kwargs={'pk': movie.pk})


    res1 = api_client.get(list_url)
    assert res1.status_code == status.HTTP_200_OK
    assert res1['X-Cache'] == 'MISS'

    res2 = api_client.get(list_url)
    assert res2.status_code == status.HTTP_200_OK
    assert res2['X-Cache'] == 'HIT'


    d1 = api_client.get(detail_url)
    assert d1.status_code == status.HTTP_200_OK
    assert d1['X-Cache'] == 'MISS'
    assert d1.data['title'] == 'Dune'

    d2 = api_client.get(detail_url)
    assert d2.status_code == status.HTTP_200_OK
    assert d2['X-Cache'] == 'HIT'


@pytest.mark.django_db(transaction=True)
def test_movie_register_update_delete_and_soft_deactivate(make_tenant, create_user):
    cinema, _, client = make_tenant('test_movie_crud', 'Movie Cinema', 'movie-crud.lvh.me')
    mgr_user = create_user(username='mv_mgr', email='mv_mgr@example.com', phone_number='+989126660001')

    register_url = reverse('cinemas:movie-register')


    assert client.post(register_url, {}, format='json').status_code == status.HTTP_401_UNAUTHORIZED

    client.force_authenticate(user=mgr_user)

    with patch('cinemas.api.v1.permissions.IsCinemaManagerOrStaffForMovie.has_permission', return_value=True), \
         patch('cinemas.api.v1.permissions.IsCinemaManagerOrStaffForMovie.has_object_permission', return_value=True), \
         patch('cinemas.signals._safe_index_movie'), \
         patch('cinemas.signals._safe_delete_movie'):

        res_create = client.post(
            register_url,
            {
                'title': 'Tenet',
                'description': 'Time inversion thriller',
                'genre': Movie.GenreChoices.ACTION,
                'duration_minutes': 150,
            },
            format='json',
        )
        assert res_create.status_code == status.HTTP_201_CREATED
        movie = Movie.objects.get(title='Tenet')
        assert movie.created_by_cinema_id == cinema.id

        manage_url = reverse('cinemas:movie-update-delete', kwargs={'pk': movie.pk})


        res_patch = client.patch(manage_url, {'duration_minutes': 152}, format='json')
        assert res_patch.status_code == status.HTTP_200_OK
        movie.refresh_from_db()
        assert movie.duration_minutes == 152


        with patch.object(Movie, 'delete', side_effect=ProtectedError('protected', set())):
            res_protected = client.delete(manage_url)
            assert res_protected.status_code == status.HTTP_200_OK
            movie.refresh_from_db()
            assert movie.is_active is False


        res_del = client.delete(manage_url)
        assert res_del.status_code == status.HTTP_204_NO_CONTENT
        assert not Movie.objects.filter(pk=movie.pk).exists()