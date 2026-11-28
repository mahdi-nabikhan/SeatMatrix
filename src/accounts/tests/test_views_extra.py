from unittest.mock import patch

import pytest
from django.conf import settings
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIRequestFactory
from rest_framework_simplejwt.tokens import RefreshToken

from accounts.api.v1.views import CookieTokenRefreshApiView


@pytest.mark.django_db
def test_cookie_token_refresh_view_success_and_missing_cookie(create_user):
    user = create_user()
    jwt_cfg = getattr(settings, 'SIMPLE_JWT', {})
    access_cookie = jwt_cfg.get('AUTH_COOKIE', 'access_token')
    refresh_cookie = jwt_cfg.get('AUTH_COOKIE_REFRESH', 'refresh_token')

    factory = APIRequestFactory()
    view = CookieTokenRefreshApiView.as_view()

    req_ok = factory.post('/token/refresh/', {}, format='json')
    req_ok.COOKIES[refresh_cookie] = str(RefreshToken.for_user(user))
    res_ok = view(req_ok)
    assert res_ok.status_code == status.HTTP_200_OK
    assert res_ok.cookies[access_cookie].value

    req_bad = factory.post('/token/refresh/', {}, format='json')
    res_bad = view(req_bad)
    assert res_bad.status_code == status.HTTP_401_UNAUTHORIZED


@pytest.mark.django_db
@pytest.mark.parametrize(
    'role_target,expected_redirect',
    [
        ('accounts.api.v1.views.Manager.objects.filter', 'manager'),
        ('accounts.api.v1.views.Staff.objects.filter', 'staff'),
    ],
)
def test_login_views_redirect_by_user_role(api_client, create_user, role_target, expected_redirect):
    create_user(username='role_user', email='role@example.com', password='StrongPassword123!')
    url = reverse('accounts-v1:login-email')

    with patch(role_target) as mock_role:
        mock_role.return_value.exists.return_value = True
        res = api_client.post(
            url,
            {'email': 'role@example.com', 'password': 'StrongPassword123!'},
            format='json',
        )

    assert res.status_code == status.HTTP_200_OK
    assert res.data['redirect_url'] == expected_redirect