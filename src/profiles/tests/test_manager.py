import pytest
from django.contrib.auth import get_user_model
from django.urls import reverse
from rest_framework import status

from profiles.models import Manager

User = get_user_model()


@pytest.mark.django_db
def test_manager_registration_creates_user_and_profile(api_client):
    url = reverse('profile-v1:manager:manager-register')
    payload = {
        'bank_iban': 'IR1234567890123456789012',
        'user': {
            'username': 'mgr_reg',
            'email': 'mgr_reg@example.com',
            'password': 'StrongPassword123!',
            'confirm_password': 'StrongPassword123!',
            'phone_number': '+989122220001',
        },
    }

    res = api_client.post(url, payload, format='json')
    assert res.status_code == status.HTTP_201_CREATED
    assert User.objects.filter(username='mgr_reg').exists()
    assert Manager.objects.filter(
        user__username='mgr_reg',
        bank_iban='IR1234567890123456789012',
    ).exists()


@pytest.mark.django_db
def test_manager_profile_detail_auth_and_404(api_client, create_user):
    url = reverse('profile-v1:manager:manager-profile')


    assert api_client.get(url).status_code == status.HTTP_401_UNAUTHORIZED


    plain_user = create_user(username='plain_u', email='plain@example.com', phone_number='+989122220002')
    api_client.force_authenticate(user=plain_user)
    assert api_client.get(url).status_code == status.HTTP_404_NOT_FOUND


    mgr_user = create_user(username='mgr_u', email='mgr_u@example.com', phone_number='+989122220003')
    Manager.objects.create(user=mgr_user, bank_iban='IR9999999999999999999999')
    api_client.force_authenticate(user=mgr_user)

    res = api_client.get(url)
    assert res.status_code == status.HTTP_200_OK
    assert res.data['bank_iban'] == 'IR9999999999999999999999'
    assert res.data['user']['username'] == 'mgr_u'