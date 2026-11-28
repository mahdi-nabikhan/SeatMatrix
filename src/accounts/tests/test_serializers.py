from types import SimpleNamespace

import pytest
from django.conf import settings
from rest_framework_simplejwt.exceptions import InvalidToken
from rest_framework_simplejwt.tokens import RefreshToken

from accounts.api.v1.serializers import (
    ChangePasswordSerializer,
    CookieTokenRefreshSerializer,
    EmailJWTLoginSerializers,
    UserDetailSerializer,
    UserRegistrations,
)


@pytest.mark.django_db
def test_user_registration_serializer_rejects_duplicate_and_weak_password(create_user):
    create_user(
        username='taken_user',
        email='taken@example.com',
        phone_number='+989120001111',
    )


    dup_serializer = UserRegistrations(
        data={
            'username': 'taken_user',
            'email': 'taken@example.com',
            'password': 'StrongPassword123!',
            'confirm_password': 'StrongPassword123!',
            'phone_number': '+989120001111',
        }
    )
    assert dup_serializer.is_valid() is False
    assert 'username' in dup_serializer.errors
    assert 'email' in dup_serializer.errors
    assert 'phone_number' in dup_serializer.errors


    weak_serializer = UserRegistrations(
        data={
            'username': 'fresh_user',
            'email': 'fresh@example.com',
            'password': '123',
            'confirm_password': '123',
            'phone_number': '+989120002222',
        }
    )
    assert weak_serializer.is_valid() is False
    assert 'password' in weak_serializer.errors


@pytest.mark.django_db
def test_email_jwt_login_serializer_returns_tokens_and_user_info(create_user):
    user = create_user(email='jwt@example.com', password='StrongPassword123!')

    serializer = EmailJWTLoginSerializers(
        data={'email': 'jwt@example.com', 'password': 'StrongPassword123!'}
    )
    assert serializer.is_valid() is True
    assert 'access' in serializer.validated_data
    assert 'refresh' in serializer.validated_data
    assert serializer.validated_data['email'] == user.email
    assert serializer.validated_data['user-id'] == user.pk


@pytest.mark.django_db
def test_user_detail_serializer_fields(create_user):
    user = create_user(
        username='detail_user',
        email='detail@example.com',
        phone_number='+989120003333',
    )
    data = UserDetailSerializer(user).data
    assert data == {
        'email': 'detail@example.com',
        'phone_number': '+989120003333',
        'username': 'detail_user',
    }


@pytest.mark.django_db
def test_cookie_token_refresh_serializer_reads_from_cookie_and_fails_when_missing(create_user):
    user = create_user()
    refresh_cookie = getattr(settings, 'SIMPLE_JWT', {}).get('AUTH_COOKIE_REFRESH', 'refresh_token')
    refresh_token = str(RefreshToken.for_user(user))

    req_with_cookie = SimpleNamespace(COOKIES={refresh_cookie: refresh_token})
    serializer = CookieTokenRefreshSerializer(data={}, context={'request': req_with_cookie})
    assert serializer.is_valid() is True
    assert 'access' in serializer.validated_data


    req_without_cookie = SimpleNamespace(COOKIES={})
    missing_serializer = CookieTokenRefreshSerializer(data={}, context={'request': req_without_cookie})
    with pytest.raises(InvalidToken):
        missing_serializer.is_valid(raise_exception=True)


@pytest.mark.django_db
def test_change_password_serializer_validations(create_user):
    user = create_user(password='OldStrongPass123!')
    ctx = {'request': SimpleNamespace(user=user)}


    wrong_old = ChangePasswordSerializer(
        data={
            'old_password': 'WrongPassword!',
            'new_password': 'NewStrongPass456!',
            'confirm_password': 'NewStrongPass456!',
        },
        context=ctx,
    )
    assert wrong_old.is_valid() is False
    assert 'old_password' in wrong_old.errors

    # عدم تطابق پسورد جدید و تکرارش
    mismatch = ChangePasswordSerializer(
        data={
            'old_password': 'OldStrongPass123!',
            'new_password': 'NewStrongPass456!',
            'confirm_password': 'DifferentPass789!',
        },
        context=ctx,
    )
    assert mismatch.is_valid() is False

    # تکراری بودن پسورد جدید با قبلی
    same_pass = ChangePasswordSerializer(
        data={
            'old_password': 'OldStrongPass123!',
            'new_password': 'OldStrongPass123!',
            'confirm_password': 'OldStrongPass123!',
        },
        context=ctx,
    )
    assert same_pass.is_valid() is False
    assert 'new_password' in same_pass.errors

    # حالت موفق
    valid = ChangePasswordSerializer(
        data={
            'old_password': 'OldStrongPass123!',
            'new_password': 'NewStrongPass456!',
            'confirm_password': 'NewStrongPass456!',
        },
        context=ctx,
    )
    assert valid.is_valid() is True