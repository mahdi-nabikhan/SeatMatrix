from unittest.mock import patch

import pytest
from django.urls import reverse
from rest_framework import status

from profiles.models import Staff


@pytest.mark.django_db
def test_staff_me_returns_active_staff_and_hides_inactive(api_client, create_user, public_tenant):
    cinema, _ = public_tenant
    url = reverse('profile-v1:staff-me')


    assert api_client.get(url).status_code == status.HTTP_401_UNAUTHORIZED

    active_user = create_user(username='stf_active', email='stf_active@example.com', phone_number='+989123330001')
    Staff.objects.create(user=active_user, cinema=cinema, shift='FULL', is_active=True)
    api_client.force_authenticate(user=active_user)

    res = api_client.get(url)
    assert res.status_code == status.HTTP_200_OK
    assert res.data['username'] == 'stf_active'
    assert res.data['shift'] == 'FULL'


    inactive_user = create_user(username='stf_off', email='stf_off@example.com', phone_number='+989123330002')
    Staff.objects.create(user=inactive_user, cinema=cinema, shift='MORNING', is_active=False)
    api_client.force_authenticate(user=inactive_user)

    assert api_client.get(url).status_code == status.HTTP_404_NOT_FOUND


@pytest.mark.django_db(transaction=True)
def test_staff_list_and_detail_crud_for_manager(make_tenant, create_user):
    cinema, _, client = make_tenant('test_staff_crud', 'Staff Cinema', 'staff-crud.lvh.me')
    mgr_user = create_user(username='stf_mgr', email='stf_mgr@example.com', phone_number='+989123330003')
    staff_user = create_user(username='stf_emp', email='stf_emp@example.com', phone_number='+989123330004')
    staff = Staff.objects.create(user=staff_user, cinema=cinema, shift='MORNING', is_active=True)

    list_url = reverse('profile-v1:staff-list')
    detail_url = reverse('profile-v1:staff-detail', kwargs={'pk': staff.pk})

    client.force_authenticate(user=mgr_user)

    with patch('cinemas.api.v1.permissions.IsCinemaManager.has_permission', return_value=True):
        res_list = client.get(list_url)
        assert res_list.status_code == status.HTTP_200_OK
        assert len(res_list.data) == 1
        assert res_list.data[0]['username'] == 'stf_emp'

        res_patch = client.patch(detail_url, {'shift': 'EVENING', 'is_active': False}, format='json')
        assert res_patch.status_code == status.HTTP_200_OK
        staff.refresh_from_db()
        assert staff.shift == 'EVENING'
        assert staff.is_active is False

        res_del = client.delete(detail_url)
        assert res_del.status_code == status.HTTP_204_NO_CONTENT
        assert not Staff.objects.filter(pk=staff.pk).exists()

@pytest.mark.django_db(transaction=True)
def test_staff_list_is_isolated_by_tenant_cinema(make_tenant, create_user):
    """مدیر سینمای B نباید کارمندان سینمای A را در لیست ببیند."""
    tenant_a, _, client_a = make_tenant('test_prof_a', 'Cinema A', 'prof-a.lvh.me')
    tenant_b, _, client_b = make_tenant('test_prof_b', 'Cinema B', 'prof-b.lvh.me')

    user_a = create_user(username='emp_a', email='emp_a@example.com', phone_number='+989123330005')
    Staff.objects.create(user=user_a, cinema=tenant_a, shift='MORNING')

    mgr_user = create_user(username='iso_mgr', email='iso_mgr@example.com', phone_number='+989123330006')
    client_a.force_authenticate(user=mgr_user)
    client_b.force_authenticate(user=mgr_user)

    list_url = reverse('profile-v1:staff-list')

    with patch('cinemas.api.v1.permissions.IsCinemaManager.has_permission', return_value=True):
        res_a = client_a.get(list_url)
        assert res_a.status_code == status.HTTP_200_OK
        assert len(res_a.data) == 1

        res_b = client_b.get(list_url)
        assert res_b.status_code == status.HTTP_200_OK
        assert len(res_b.data) == 0