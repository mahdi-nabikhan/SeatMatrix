import pytest
from django.db import connection
from django.urls import reverse
from rest_framework import status

from cinemas.models import Cinema
from profiles.models import Manager


@pytest.mark.django_db
def test_cinema_list_detail_and_update(api_client, public_tenant):
    cinema, _ = public_tenant


    res_list = api_client.get(reverse('cinemas:cinema-list'))
    assert res_list.status_code == status.HTTP_200_OK
    assert any(c['name'] == cinema.name for c in res_list.data)


    res_detail = api_client.get(reverse('cinemas:cinema-detail', kwargs={'pk': cinema.pk}))
    assert res_detail.status_code == status.HTTP_200_OK
    assert res_detail.data['name'] == cinema.name
    assert res_detail.data['manager'] is None


    res_patch = api_client.patch(
        reverse('cinemas:cinema-update', kwargs={'pk': cinema.pk}),
        {'description': 'Updated description'},
        format='json',
    )
    assert res_patch.status_code == status.HTTP_200_OK
    cinema.refresh_from_db()
    assert cinema.description == 'Updated description'


@pytest.mark.django_db(transaction=True)
def test_cinema_register_and_delete_by_manager(api_client):
    register_url = reverse('cinemas:cinema-register')
    delete_url = reverse('cinemas:cinema-delete')
    schema_name = 'test_reg_cinema'

    payload = {
        'schema_name': schema_name,
        'name': 'Azadi Cinema',
        'description': 'Flagship cinema',
        'manager': {
            'bank_iban': 'IR1234567890123456789012',
            'user': {
                'username': 'azadi_mgr',
                'email': 'azadi_mgr@example.com',
                'password': 'StrongPassword123!',
                'confirm_password': 'StrongPassword123!',
                'phone_number': '+989125550001',
            },
        },
    }

    try:
        res_reg = api_client.post(register_url, payload, format='json')
        assert res_reg.status_code == status.HTTP_201_CREATED
        cinema = Cinema.objects.get(schema_name=schema_name)
        assert cinema.manager is not None


        assert api_client.delete(delete_url).status_code == status.HTTP_401_UNAUTHORIZED

        api_client.force_authenticate(user=cinema.manager.user)
        res_del = api_client.delete(delete_url)
        assert res_del.status_code == status.HTTP_204_NO_CONTENT
        assert not Cinema.objects.filter(schema_name=schema_name).exists()
    finally:
        connection.set_schema_to_public()
        with connection.cursor() as cursor:
            cursor.execute(f'DROP SCHEMA IF EXISTS "{schema_name}" CASCADE')