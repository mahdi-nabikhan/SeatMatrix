from unittest.mock import patch

import pytest
from django.conf import settings
from django.contrib.auth import get_user_model
from django.urls import reverse
from rest_framework import status

User = get_user_model()


def _cookie_names():
    jwt_cfg = getattr(settings, 'SIMPLE_JWT', {})
    return (
        jwt_cfg.get('AUTH_COOKIE', 'access_token'),
        jwt_cfg.get('AUTH_COOKIE_REFRESH', 'refresh_token'),
    )


@pytest.mark.django_db
def test_user_registration_success(api_client):
    url = reverse('accounts-v1:user-register')
    payload = {
        'username': 'newuser',
        'email': 'newuser@example.com',
        'password': 'StrongPassword123!',
        'confirm_password': 'StrongPassword123!',
        'phone_number': '+989123456789',
    }

    res = api_client.post(url, payload, format='json')
    assert res.status_code == status.HTTP_201_CREATED
    assert User.objects.filter(email='newuser@example.com').exists()


@pytest.mark.django_db
def test_user_registration_fails_on_mismatched_password_and_short_phone(api_client):
    url = reverse('accounts-v1:user-register')

    res_mismatch = api_client.post(
        url,
        {
            'username': 'u1',
            'email': 'u1@example.com',
            'password': 'StrongPassword123!',
            'confirm_password': 'DifferentPassword123!',
            'phone_number': '+989123456789',
        },
        format='json',
    )
    assert res_mismatch.status_code == status.HTTP_400_BAD_REQUEST

    res_short_phone = api_client.post(
        url,
        {
            'username': 'u2',
            'email': 'u2@example.com',
            'password': 'StrongPassword123!',
            'confirm_password': 'StrongPassword123!',
            'phone_number': '0912345',
        },
        format='json',
    )
    assert res_short_phone.status_code == status.HTTP_400_BAD_REQUEST


@pytest.mark.django_db
def test_email_login_sets_jwt_cookies_and_redirect_url(api_client, create_user):
    user = create_user(email='login@example.com', password='StrongPassword123!')
    url = reverse('accounts-v1:login-email')
    access_cookie, refresh_cookie = _cookie_names()

    with patch('accounts.api.v1.views.Customer.objects.filter') as mock_customer:
        mock_customer.return_value.exists.return_value = True
        res = api_client.post(
            url,
            {'email': 'login@example.com', 'password': 'StrongPassword123!'},
            format='json',
        )

    assert res.status_code == status.HTTP_200_OK
    assert res.data['user_id'] == user.id
    assert res.data['redirect_url'] == 'customer'
    assert res.cookies[access_cookie].value
    assert res.cookies[refresh_cookie].value
    assert res.cookies[access_cookie]['httponly'] is True


@pytest.mark.django_db
def test_username_login_success_and_wrong_password(api_client, create_user):
    user = create_user(username='mahdi_dev', password='StrongPassword123!')
    url = reverse('accounts-v1:login-username')
    access_cookie, refresh_cookie = _cookie_names()

    bad_res = api_client.post(
        url,
        {'username': 'mahdi_dev', 'password': 'WrongPassword!'},
        format='json',
    )
    assert bad_res.status_code == status.HTTP_400_BAD_REQUEST

    ok_res = api_client.post(
        url,
        {'username': 'mahdi_dev', 'password': 'StrongPassword123!'},
        format='json',
    )
    assert ok_res.status_code == status.HTTP_200_OK
    assert ok_res.data['user_id'] == user.id
    assert ok_res.cookies[access_cookie].value
    assert ok_res.cookies[refresh_cookie].value


@pytest.mark.django_db
def test_check_auth_and_logout_clears_cookies(api_client, create_user):
    user = create_user(username='auth_user')
    check_url = reverse('accounts-v1:check')
    logout_url = reverse('accounts-v1:logout')
    access_cookie, refresh_cookie = _cookie_names()

 
    unauth_logout = api_client.post(logout_url)
    assert unauth_logout.status_code == status.HTTP_401_UNAUTHORIZED

  
    api_client.force_authenticate(user=user)

    check_res = api_client.get(check_url)
    assert check_res.status_code == status.HTTP_200_OK
    assert check_res.data['detail'] == 'auth_user'

    logout_res = api_client.post(logout_url)
    assert logout_res.status_code == status.HTTP_200_OK
    assert logout_res.cookies[access_cookie].value == ''
    assert logout_res.cookies[refresh_cookie].value == ''