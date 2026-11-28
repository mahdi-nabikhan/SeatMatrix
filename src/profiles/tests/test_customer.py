import pytest
from django.contrib.auth import get_user_model
from django.urls import reverse
from rest_framework import status

from profiles.models import Customer

User = get_user_model()


@pytest.mark.django_db
def test_customer_registration_creates_user_and_profile(api_client):
    url = reverse('profile-v1:customer:customer-register')
    payload = {
        'firstname': 'Mahdi',
        'last_name': 'Nabikhan',
        'age': '24',
        'user': {
            'username': 'cust_reg',
            'email': 'cust_reg@example.com',
            'password': 'StrongPassword123!',
            'confirm_password': 'StrongPassword123!',
            'phone_number': '+989121110001',
        },
    }

    res = api_client.post(url, payload, format='json')
    assert res.status_code == status.HTTP_201_CREATED
    assert User.objects.filter(username='cust_reg').exists()
    assert Customer.objects.filter(user__username='cust_reg', firstname='Mahdi').exists()


@pytest.mark.django_db
def test_customer_registration_rolls_back_on_invalid_user(api_client):
    url = reverse('profile-v1:customer:customer-register')
    payload = {
        'firstname': 'Bad',
        'last_name': 'User',
        'user': {
            'username': 'bad_cust',
            'email': 'bad_cust@example.com',
            'password': 'StrongPassword123!',
            'confirm_password': 'WrongPassword!',
            'phone_number': '+989121110002',
        },
    }

    res = api_client.post(url, payload, format='json')
    assert res.status_code == status.HTTP_400_BAD_REQUEST
    assert not User.objects.filter(username='bad_cust').exists()
    assert not Customer.objects.filter(firstname='Bad').exists()


@pytest.mark.django_db(transaction=True)
def test_customer_profile_detail_update_and_delete(make_tenant, create_user):
    _, _, client = make_tenant('test_cust_crud', 'Cust Cinema', 'cust-crud.lvh.me')
    user = create_user(username='cust_crud', email='cust_crud@example.com', phone_number='+989121110003')
    Customer.objects.create(user=user, firstname='Sara', last_name='Ahmadi', age='22')

    detail_url = reverse('profile-v1:customer:customer-profile')
    edit_url = reverse('profile-v1:customer:customer-profile-edit')
    delete_url = reverse('profile-v1:customer:customer-profile-delete')

    assert client.get(detail_url).status_code == status.HTTP_401_UNAUTHORIZED
    assert client.delete(delete_url).status_code == status.HTTP_401_UNAUTHORIZED

    client.force_authenticate(user=user)


    res_get = client.get(detail_url)
    assert res_get.status_code == status.HTTP_200_OK
    assert res_get.data['firstname'] == 'Sara'
    assert res_get.data['user']['email'] == 'cust_crud@example.com'

  
    res_patch = client.patch(edit_url, {'age': '23'}, format='json')
    assert res_patch.status_code == status.HTTP_200_OK
    assert Customer.objects.get(user=user).age == '23'

  
    res_put = client.put(
        edit_url,
        {'firstname': 'Zahra', 'last_name': 'Karimi', 'age': '28'},
        format='json',
    )
    assert res_put.status_code == status.HTTP_200_OK
    updated = Customer.objects.get(user=user)
    assert updated.firstname == 'Zahra'
    assert updated.last_name == 'Karimi'


    res_del = client.delete(delete_url)
    assert res_del.status_code == status.HTTP_200_OK
    assert not Customer.objects.filter(user=user).exists()

@pytest.mark.django_db
def test_customer_profile_returns_404_when_user_has_no_customer_profile(api_client, create_user):
    user = create_user(username='no_cust', email='no_cust@example.com', phone_number='+989121110004')
    api_client.force_authenticate(user=user)

    res = api_client.get(reverse('profile-v1:customer:customer-profile'))
    assert res.status_code == status.HTTP_404_NOT_FOUND