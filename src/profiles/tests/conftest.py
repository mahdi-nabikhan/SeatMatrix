import pytest
from django.contrib.auth import get_user_model
from django.db import connection
from rest_framework.test import APIClient

from cinemas.models import Cinema, CinemaDomain

User = get_user_model()


@pytest.fixture
def public_tenant(db):
    connection.set_schema_to_public()
    tenant, _ = Cinema.objects.get_or_create(
        schema_name='public',
        defaults={'name': 'Public Cinema'},
    )
    domain, _ = CinemaDomain.objects.get_or_create(
        domain='testserver',
        defaults={'tenant': tenant, 'is_primary': True},
    )
    return tenant, domain


@pytest.fixture
def api_client(public_tenant):
    return APIClient(HTTP_HOST='testserver')


@pytest.fixture
def create_user(db):
    def _create(
        username='profile_user',
        email='profile@example.com',
        password='StrongPassword123!',
        phone_number='+989121234567',
    ):
        return User.objects.create_user(
            username=username,
            email=email,
            password=password,
            phone_number=phone_number,
        )

    return _create