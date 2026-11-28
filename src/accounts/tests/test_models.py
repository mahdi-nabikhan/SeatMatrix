from datetime import timedelta

import pytest
from django.contrib.auth import get_user_model
from django.utils import timezone

from accounts.models import OTP

User = get_user_model()


@pytest.mark.django_db
def test_create_user_and_superuser():
    user = User.objects.create_user(
        username='ali_user',
        email='Ali@Example.com',
        password='StrongPassword123!',
        phone_number='+989120000001',
    )
    assert user.email == 'Ali@example.com'
    assert user.check_password('StrongPassword123!')
    assert user.is_active is True
    assert user.is_staff is False
    assert user.is_superuser is False

    admin = User.objects.create_superuser(
        username='admin_user',
        email='admin@example.com',
        password='StrongPassword123!',
        phone_number='+989120000002',
    )
    assert admin.is_staff is True
    assert admin.is_superuser is True


@pytest.mark.django_db
def test_create_user_requires_username_and_email():
    with pytest.raises(ValueError):
        User.objects.create_user(username='', email='a@b.com', password='StrongPassword123!')

    with pytest.raises(ValueError):
        User.objects.create_user(username='u1', email='', password='StrongPassword123!')


@pytest.mark.django_db
def test_otp_is_valid_lifecycle(create_user):
    user = create_user()
    otp = OTP.objects.create(user=user, code='123456')


    assert otp.is_valid() is True


    otp.is_used = True
    otp.save()
    assert otp.is_valid() is False

   
    expired_otp = OTP.objects.create(user=user, code='654321')
    OTP.objects.filter(id=expired_otp.id).update(
        created_at=timezone.now() - timedelta(minutes=3)
    )
    expired_otp.refresh_from_db()
    assert expired_otp.is_valid() is False