from datetime import timedelta
import urllib.error
from unittest.mock import patch

import pytest
from django.urls import reverse
from django.utils import timezone
from django_tenants.utils import schema_context
from rest_framework import status

from cinemas.models import Movie
from operations.models import Address, CinemaBranch, Hall, Showtime


def _create_branch_with_showtime(movie: Movie, branch_name: str):
    address = Address.objects.create(
        province='Tehran',
        city='Tehran',
        full_address='Valiasr St, No 10',
    )
    branch = CinemaBranch.objects.create(
        address=address,
        branch_name=branch_name,
    )
    hall = Hall.objects.create(
        branch=branch,
        name='Hall 1',
        capacity=100,
    )
    showtime = Showtime.objects.create(
        hall=hall,
        movie=movie,
        start_time=timezone.now() + timedelta(hours=3),
        base_price=150000,
    )
    return branch, hall, showtime


@pytest.mark.django_db(transaction=True)
def test_operations_records_are_isolated_between_tenant_schemas(make_tenant):
    """شعبه، سالن و سانس ثبت‌شده در تننت A نباید در اسکیمای تننت B قابل مشاهده باشد."""
    tenant_a, _, _ = make_tenant('test_iso_a', 'Cinema A', 'cinema-a.lvh.me')
    tenant_b, _, _ = make_tenant('test_iso_b', 'Cinema B', 'cinema-b.lvh.me')

    movie = Movie.objects.create(
        title='Inception',
        description='Dream heist sci-fi',
        genre=Movie.GenreChoices.SCI_FI,
        duration_minutes=148,
    )

    with schema_context(tenant_a.schema_name):
        branch_a, hall_a, showtime_a = _create_branch_with_showtime(movie, 'Cinema A Main')
        assert CinemaBranch.objects.filter(id=branch_a.id).exists()
        assert Hall.objects.filter(id=hall_a.id).exists()
        assert Showtime.objects.filter(id=showtime_a.id).exists()

    with schema_context(tenant_b.schema_name):
        assert CinemaBranch.objects.count() == 0
        assert Hall.objects.count() == 0
        assert Showtime.objects.count() == 0


@pytest.mark.django_db(transaction=True)
def test_http_host_routes_each_request_to_correct_tenant_schema(make_tenant):
    """هر دامنه باید در لایه Middleware به اسکیمای اختصاصی خودش متصل شود."""
    tenant_a, _, client_a = make_tenant('test_route_a', 'Cinema A', 'route-a.lvh.me')
    tenant_b, _, client_b = make_tenant('test_route_b', 'Cinema B', 'route-b.lvh.me')

    url = reverse('cinemas:movie-search')

    res_a = client_a.get(url)
    assert res_a.status_code == status.HTTP_200_OK
    assert res_a.wsgi_request.tenant.schema_name == tenant_a.schema_name

    res_b = client_b.get(url)
    assert res_b.status_code == status.HTTP_200_OK
    assert res_b.wsgi_request.tenant.schema_name == tenant_b.schema_name


@pytest.mark.django_db(transaction=True)
@patch('cinemas.search._search_es', side_effect=urllib.error.URLError('skip es in isolation test'))
def test_only_showing_search_api_is_isolated_between_tenants(_mock_es, make_tenant):
    """فیلمی که فقط در سینمای A سانس دارد، نباید در سرچ only_showing سینمای B نمایش داده شود."""
    tenant_a, _, client_a = make_tenant('test_api_a', 'Cinema A', 'api-a.lvh.me')
    tenant_b, _, client_b = make_tenant('test_api_b', 'Cinema B', 'api-b.lvh.me')

    movie = Movie.objects.create(
        title='Interstellar',
        description='Space exploration drama',
        genre=Movie.GenreChoices.SCI_FI,
        duration_minutes=169,
    )

    with schema_context(tenant_a.schema_name):
        _create_branch_with_showtime(movie, 'Cinema A Branch')

    url = reverse('cinemas:movie-search') + '?only_showing=true'

    res_a = client_a.get(url)
    assert res_a.status_code == status.HTTP_200_OK
    assert res_a.data['count'] == 1
    assert res_a.data['results'][0]['id'] == movie.id

    res_b = client_b.get(url)
    assert res_b.status_code == status.HTTP_200_OK
    assert res_b.data['count'] == 0