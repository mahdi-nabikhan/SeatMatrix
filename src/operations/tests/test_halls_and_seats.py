import pytest
from django_tenants.utils import schema_context
from rest_framework import status

from operations.models import Address, CinemaBranch, Hall, Seat

from .conftest import op_url


@pytest.mark.django_db(transaction=True)
def test_halls_and_seats_lifecycle_and_capacity_enforcement(setup_cinema_roles):
    env = setup_cinema_roles('test_ops_hall', 'Hall Cinema', 'ops-hall.lvh.me')
    client = env['client']
    tenant = env['tenant']

    with schema_context(tenant.schema_name):
        addr = Address.objects.create(province='Tehran', city='Tehran', full_address='Main St')
        branch = CinemaBranch.objects.create(address=addr, branch_name='Central')
        branch.branch_admins.add(env['staff'])
        branch_id = branch.id


    client.force_authenticate(user=env['staff_user'])
    res_hall = client.post(
        op_url('hall-register', pk=branch_id),
        {'name': 'Hall 1', 'hall_type': 'VIP', 'capacity': 6},
        format='json',
    )
    assert res_hall.status_code == status.HTTP_201_CREATED
    hall_id = res_hall.data['data']['id']


    client.force_authenticate(user=None)
    res_detail = client.get(op_url('hall-detail', hall_id=hall_id))
    assert res_detail.status_code == status.HTTP_200_OK
    assert res_detail.data['name'] == 'Hall 1'


    client.force_authenticate(user=env['staff_user'])
    res_bulk = client.post(
        op_url('seat-bulk-create'),
        {'hall': hall_id, 'rows': ['A', 'B'], 'seats_per_row': 2, 'vip_rows': ['A']},
        format='json',
    )
    assert res_bulk.status_code == status.HTTP_201_CREATED


    res_overflow = client.post(
        op_url('seat-bulk-create'),
        {'hall': hall_id, 'rows': ['C', 'D'], 'seats_per_row': 2},
        format='json',
    )
    assert res_overflow.status_code == status.HTTP_400_BAD_REQUEST


    res_seats = client.get(op_url('seat-list', hall_pk=hall_id))
    assert res_seats.status_code == status.HTTP_200_OK
    assert len(res_seats.data) == 4
    assert res_seats.data[0]['is_vip'] is True


    assert client.delete(op_url('hall-manage', pk=hall_id)).status_code == status.HTTP_200_OK

    branch_halls_url = op_url('branch-hall-list-create', branch_id=branch_id)
    client.force_authenticate(user=None)
    assert len(client.get(branch_halls_url).data) == 0

    client.force_authenticate(user=env['manager_user'])
    assert len(client.get(branch_halls_url).data) == 1

    client.force_authenticate(user=env['staff_user'])
    assert client.delete(op_url('hall-detail', hall_id=hall_id)).status_code == status.HTTP_403_FORBIDDEN

    client.force_authenticate(user=env['manager_user'])
    assert client.delete(op_url('hall-detail', hall_id=hall_id)).status_code == status.HTTP_204_NO_CONTENT
    with schema_context(tenant.schema_name):
        assert not Hall.objects.filter(id=hall_id).exists()
        assert Seat.objects.filter(hall_id=hall_id).count() == 0