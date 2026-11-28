from datetime import timedelta

import pytest
from django.conf import settings
from django.urls import reverse
from django.utils import timezone
from rest_framework import status

from accounts.models import OTP


@pytest.mark.django_db
def test_request_otp_success_and_unknown_phone(api_client, create_user):
    user = create_user(phone_number='+989121112233')
    url = reverse('accounts-v1:otp_request')

    res_ok = api_client.post(url, {'phone_number': '+989121112233'}, format='json')
    assert res_ok.status_code == status.HTTP_200_OK
    assert OTP.objects.filter(user=user, is_used=False).count() == 1

    res_missing = api_client.post(url, {'phone_number': '+989999999999'}, format='json')
    assert res_missing.status_code == status.HTTP_400_BAD_REQUEST


@pytest.mark.django_db
def test_verify_otp_login_success_and_prevents_reuse(api_client, create_user):
    user = create_user(phone_number='+989121112244')
    otp = OTP.objects.create(user=user, code='482910')
    url = reverse('accounts-v1:otp_verify')

    access_cookie = getattr(settings, 'SIMPLE_JWT', {}).get('AUTH_COOKIE', 'access_token')


    res = api_client.post(
        url,
        {'phone_number': '+989121112244', 'code': '482910'},
        format='json',
    )
    assert res.status_code == status.HTTP_200_OK
    assert res.data['user_id'] == user.id
    assert res.cookies[access_cookie].value

    otp.refresh_from_db()
    assert otp.is_used is True


    reuse_res = api_client.post(
        url,
        {'phone_number': '+989121112244', 'code': '482910'},
        format='json',
    )
    assert reuse_res.status_code == status.HTTP_400_BAD_REQUEST


@pytest.mark.django_db
def test_verify_otp_rejects_wrong_and_expired_code(api_client, create_user):
    user = create_user(phone_number='+989121112255')
    otp = OTP.objects.create(user=user, code='999888')
    url = reverse('accounts-v1:otp_verify')

    # کد اشتباه
    wrong_res = api_client.post(
        url,
        {'phone_number': '+989121112255', 'code': '000000'},
        format='json',
    )
    assert wrong_res.status_code == status.HTTP_400_BAD_REQUEST

    # منقضی کردن کد
    OTP.objects.filter(id=otp.id).update(created_at=timezone.now() - timedelta(minutes=3))
    expired_res = api_client.post(
        url,
        {'phone_number': '+989121112255', 'code': '999888'},
        format='json',
    )
    assert expired_res.status_code == status.HTTP_400_BAD_REQUEST