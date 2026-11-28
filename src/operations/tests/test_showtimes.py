from datetime import timedelta

import pytest
from django.utils import timezone
from django_tenants.utils import schema_context
from rest_framework import status

from cinemas.models import Movie
from operations.models import Address, CinemaBranch, Hall, Seat, ShowtimeSeat

from .conftest import op_url


@pytest.mark.django_db(transaction=True)
def test_showtime_creation_seat_generation_and_status_updates(setup_cinema_roles):
    env = setup_cinema_roles('test_ops_show', 'Show Cinema', 'ops-show.lvh.me')
    client = env['client']
    tenant = env['tenant']

    active_movie = Movie.objects.create(
        title='Oppenheimer',
        description='Biographical thriller',
        genre=Movie.GenreChoices.DRAMA,
        duration_minutes=180,
        is_active=True,
    )
    inactive_movie = Movie.objects.create(
        title='Archived Film',
        description='No longer showing',
        genre=Movie.GenreChoices.DRAMA,
        duration_minutes=90,
        is_active=False,
    )

    with schema_context(tenant.schema_name):
        addr = Address.objects.create(province='Tehran', city='Tehran', full_address='North St')
        branch = CinemaBranch.objects.create(address=addr, branch_name='North Branch')
        branch.branch_admins.add(env['staff'])
        empty_hall = Hall.objects.create(branch=branch, name='Empty Hall', capacity=10)
        hall = Hall.objects.create(branch=branch, name='IMAX Hall', hall_type='IMAX', capacity=10)
        Seat.objects.create(hall=hall, row_label='A', seat_number=1, is_vip=True)
        Seat.objects.create(hall=hall, row_label='A', seat_number=2, is_vip=True)
        empty_hall_id, hall_id = empty_hall.id, hall.id

    create_url = op_url('showtime-create')
    future_time = (timezone.now() + timedelta(days=1)).isoformat()
    past_time = (timezone.now() - timedelta(hours=2)).isoformat()

    client.force_authenticate(user=env['staff_user'])


    assert client.post(
        create_url,
        {'hall': empty_hall_id, 'movie': active_movie.id, 'start_time': future_time, 'base_price': 150000},
        format='json',
    ).status_code == status.HTTP_400_BAD_REQUEST


    assert client.post(
        create_url,
        {'hall': hall_id, 'movie': inactive_movie.id, 'start_time': future_time, 'base_price': 150000},
        format='json',
    ).status_code == status.HTTP_400_BAD_REQUEST


    assert client.post(
        create_url,
        {'hall': hall_id, 'movie': active_movie.id, 'start_time': past_time, 'base_price': 150000},
        format='json',
    ).status_code == status.HTTP_400_BAD_REQUEST


    res_create = client.post(
        create_url,
        {'hall': hall_id, 'movie': active_movie.id, 'start_time': future_time, 'base_price': 150000},
        format='json',
    )
    assert res_create.status_code == status.HTTP_201_CREATED
    showtime_id = res_create.data['id']

  
    res_detail = client.get(op_url('showtime-detail', pk=showtime_id))
    assert res_detail.status_code == status.HTTP_200_OK
    assert len(res_detail.data['showtime_seats']) == 2
    first_st_seat_id = res_detail.data['showtime_seats'][0]['id']


    res_status = client.patch(
        op_url('showtime-seat-status', pk=first_st_seat_id),
        {'status': 'SOLD'},
        format='json',
    )
    assert res_status.status_code == status.HTTP_200_OK
    with schema_context(tenant.schema_name):
        assert ShowtimeSeat.objects.get(id=first_st_seat_id).status == 'SOLD'

    client.force_authenticate(user=None)
    res_active = client.get(op_url('active-movie-showtimes'))
    assert res_active.status_code == status.HTTP_200_OK
    assert len(res_active.data) == 1
    assert res_active.data[0]['title'] == 'Oppenheimer'
    assert len(res_active.data[0]['showtimes']) == 1