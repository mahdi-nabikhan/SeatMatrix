import pytest
from django_tenants.utils import schema_context
from rest_framework import status

from operations.models import CinemaBranch

from .conftest import op_url


@pytest.mark.django_db(transaction=True)
def test_branch_crud_permissions_and_branch_admins(setup_cinema_roles):
    env = setup_cinema_roles('test_ops_branch', 'Branch Cinema', 'ops-branch.lvh.me')
    client = env['client']
    tenant = env['tenant']

    register_url = op_url('branch-register')
    list_url = op_url('branch-list')

    branch_payload = {
        'branch_name': 'Vanak Branch',
        'phone_number': '02188887777',
        'facilities': ['Parking', 'Cafe'],
        'address': {
            'province': 'Tehran',
            'city': 'Tehran',
            'full_address': 'Vanak Square, Valiasr St',
            'postal_code': '1234567890',
        },
    }


    client.force_authenticate(user=env['regular_user'])
    assert client.post(register_url, branch_payload, format='json').status_code == status.HTTP_403_FORBIDDEN


    client.force_authenticate(user=env['manager_user'])
    res_create = client.post(register_url, branch_payload, format='json')
    assert res_create.status_code == status.HTTP_201_CREATED
    branch_id = res_create.data['data']['id']


    client.force_authenticate(user=None)
    res_list = client.get(list_url)
    assert res_list.status_code == status.HTTP_200_OK
    assert len(res_list.data) == 1
    assert res_list.data[0]['city'] == 'Tehran'

    res_detail = client.get(op_url('branch-detail', pk=branch_id))
    assert res_detail.status_code == status.HTTP_200_OK
    assert res_detail.data['address']['province'] == 'Tehran'


    client.force_authenticate(user=env['manager_user'])
    res_adm = client.post(
        op_url('branch-admin-register', branch_id=branch_id),
        {
            'email': 'badmin@example.com',
            'username': 'branch_adm1',
            'phone_number': '+989151112233',
            'password': 'StrongPassword123!',
            'shift': 'EVENING',
        },
        format='json',
    )
    assert res_adm.status_code == status.HTTP_201_CREATED
    new_staff_id = res_adm.data['staff_id']


    res_adm_list = client.get(op_url('branch-admin-list', branch_id=branch_id))
    assert res_adm_list.status_code == status.HTTP_200_OK
    assert len(res_adm_list.data) == 1

   
    with schema_context(tenant.schema_name):
        branch = CinemaBranch.objects.get(id=branch_id)
        branch.branch_admins.add(env['staff'])

    manage_url = op_url('branch-manage', pk=branch_id)
    client.force_authenticate(user=env['staff_user'])
    assert client.patch(manage_url, {'phone_number': '02199990000'}, format='json').status_code == status.HTTP_200_OK
    assert client.delete(manage_url).status_code == status.HTTP_403_FORBIDDEN

    # حذف ادمین شعبه و سپس غیرفعال کردن شعبه توسط مدیر سینما
    client.force_authenticate(user=env['manager_user'])
    assert client.delete(op_url('branch-admin-remove', branch_id=branch_id, staff_id=new_staff_id)).status_code == status.HTTP_204_NO_CONTENT
    assert client.delete(manage_url).status_code == status.HTTP_200_OK

    with schema_context(tenant.schema_name):
        assert CinemaBranch.objects.get(id=branch_id).is_active is False