import pytest
from django.db import connection
from rest_framework.test import APIClient

from cinemas.models import Cinema, CinemaDomain


@pytest.fixture
def make_tenant(transactional_db):

    created_schemas = []

    def _create(schema_name: str, name: str, domain: str):
        connection.set_schema_to_public()
        tenant = Cinema.objects.create(schema_name=schema_name, name=name)
        domain_obj = CinemaDomain.objects.create(
            domain=domain,
            tenant=tenant,
            is_primary=True,
        )
        created_schemas.append(schema_name)
        client = APIClient(HTTP_HOST=domain_obj.domain)
        return tenant, domain_obj, client

    yield _create

    connection.set_schema_to_public()
    with connection.cursor() as cursor:
        for schema in created_schemas:
            cursor.execute(f'DROP SCHEMA IF EXISTS "{schema}" CASCADE')