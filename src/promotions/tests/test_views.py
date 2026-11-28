from datetime import timedelta
from unittest.mock import patch

import pytest
from django.utils import timezone
from django_tenants.utils import schema_context
from rest_framework import status

from cinemas.models import Movie
from operations.models import Address, CinemaBranch, Hall, Showtime
from promotions.models import Coupon, DiscountRule

from .conftest import promo_url


@pytest.mark.django_db(transaction=True)
def test_coupon_rule_crud_permissions_and_cart_preview(setup_promo_tenant):
    env = setup_promo_tenant('test_promo_api', 'Promo API Cinema', 'promo-api.lvh.me')
    client = env['client']
    tenant = env['tenant']

    coupons_url = promo_url('coupon-list-create')
    rules_url = promo_url('discount-rule-list-create')
    preview_url = promo_url('promotion-preview')


    client.force_authenticate(user=env['regular_user'])
    assert client.get(coupons_url).status_code == status.HTTP_403_FORBIDDEN
    assert client.get(rules_url).status_code == status.HTTP_403_FORBIDDEN


    client.force_authenticate(user=env['manager_user'])
    now = timezone.now()


    res_bad_dates = client.post(
        coupons_url,
        {
            'code': 'bad',
            'discount_percentage': 10,
            'valid_from': (now + timedelta(days=2)).isoformat(),
            'valid_to': (now + timedelta(days=1)).isoformat(),
        },
        format='json',
    )
    assert res_bad_dates.status_code == status.HTTP_400_BAD_REQUEST

    res_coupon = client.post(
        coupons_url,
        {'code': '  nowruz20  ', 'discount_percentage': 20, 'capacity': 10},
        format='json',
    )
    assert res_coupon.status_code == status.HTTP_201_CREATED
    assert res_coupon.data['code'] == 'NOWRUZ20'
    coupon_id = res_coupon.data['id']

    assert client.post(
        coupons_url,
        {'code': 'nowruz20', 'discount_percentage': 15},
        format='json',
    ).status_code == status.HTTP_400_BAD_REQUEST


    assert client.post(
        rules_url,
        {'name': 'Invalid Day', 'discount_percentage': 10, 'day_of_week': 7},
        format='json',
    ).status_code == status.HTTP_400_BAD_REQUEST

    res_rule = client.post(
        rules_url,
        {'name': 'سه‌شنبه نیم‌بها', 'discount_percentage': 50, 'day_of_week': 1},
        format='json',
    )
    assert res_rule.status_code == status.HTTP_201_CREATED
    assert res_rule.data['day_of_week_display'] == 'سه‌شنبه'
    rule_id = res_rule.data['id']


    movie = Movie.objects.create(
        title='Promo Movie',
        description='Test movie',
        genre=Movie.GenreChoices.COMEDY,
        duration_minutes=100,
    )
    with schema_context(tenant.schema_name):
        addr = Address.objects.create(province='Tehran', city='Tehran', full_address='Valiasr')
        branch = CinemaBranch.objects.create(address=addr, branch_name='Promo Branch')
        hall = Hall.objects.create(branch=branch, name='Hall P', capacity=10)

        start_time = now + timedelta(days=1)
        if timezone.localtime(start_time).weekday() == 1:
            start_time += timedelta(days=1)
        showtime = Showtime.objects.create(hall=hall, movie=movie, start_time=start_time, base_price=100000)
        showtime_id = showtime.id

    client.force_authenticate(user=None)


    with patch('promotions.api.v1.views._resolve_owner', return_value=('owner1', False)), \
         patch('promotions.api.v1.views.get_cart', return_value=None):
        assert client.post(preview_url, {'coupon_code': 'NOWRUZ20'}, format='json').status_code == status.HTTP_400_BAD_REQUEST


    fake_cart = {'showtime_id': showtime_id, 'seat_ids': [1, 2]}
    with patch('promotions.api.v1.views._resolve_owner', return_value=('owner1', False)), \
         patch('promotions.api.v1.views.get_cart', return_value=fake_cart):
        res_prev = client.post(preview_url, {'coupon_code': 'NOWRUZ20'}, format='json')
        assert res_prev.status_code == status.HTTP_200_OK
        assert res_prev.data['total_amount'] == 200000
        assert res_prev.data['discount_amount'] == 40000
        assert res_prev.data['final_amount'] == 160000
        assert res_prev.data['applied_type'] == 'COUPON'

    with schema_context(tenant.schema_name):
        assert Coupon.objects.get(id=coupon_id).used_count == 0


    client.force_authenticate(user=env['manager_user'])
    assert client.delete(promo_url('coupon-detail', pk=coupon_id)).status_code == status.HTTP_204_NO_CONTENT
    assert client.delete(promo_url('discount-rule-detail', pk=rule_id)).status_code == status.HTTP_204_NO_CONTENT
    with schema_context(tenant.schema_name):
        assert not Coupon.objects.filter(id=coupon_id).exists()
        assert not DiscountRule.objects.filter(id=rule_id).exists()